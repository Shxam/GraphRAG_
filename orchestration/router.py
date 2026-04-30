"""
Incident Router and Orchestration Layer
FastAPI service that routes incidents through both pipelines with async task queue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from pipelines.baseline import BaselinePipeline
from pipelines.graphrag import GraphRAGPipeline
from pipelines.comparator import Comparator
from tee.enclave_runner import EnclaveRunner
from orchestration.deduplicator import AlertDeduplicator
from graph.query_cache import cache_stats

# Try to import redis for task storage
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


app = FastAPI(title="PostMortemIQ API", version="1.0.0")

# Initialize components
enclave = EnclaveRunner()
baseline_pipeline = BaselinePipeline()
graphrag_pipeline = GraphRAGPipeline()
comparator = Comparator()
deduplicator = AlertDeduplicator(window_seconds=300)

# Task storage (Redis or in-memory fallback)
task_storage: Dict[str, Dict[str, Any]] = {}
redis_client = None

# Metrics counters
metrics = {
    "alerts_total": 0,
    "duplicates_blocked": 0,
    "llm_calls_total": 0,
    "cache_hits_total": 0,
    "avg_tokens_saved": 0
}


def get_task_storage():
    """Get task storage backend"""
    global redis_client
    if REDIS_AVAILABLE and redis_client is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            redis_client = redis.from_url(redis_url, decode_responses=True)
            redis_client.ping()
        except Exception:
            redis_client = None
    return redis_client


def store_task(task_id: str, data: Dict[str, Any]):
    """Store task data"""
    client = get_task_storage()
    if client:
        try:
            client.setex(f"task:{task_id}", 3600, json.dumps(data))
            return
        except Exception:
            pass
    # Fallback to memory
    task_storage[task_id] = data


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve task data"""
    client = get_task_storage()
    if client:
        try:
            data = client.get(f"task:{task_id}")
            if data:
                return json.loads(data)
        except Exception:
            pass
    # Fallback to memory
    return task_storage.get(task_id)


class IncidentRequest(BaseModel):
    incident_id: str
    alert_id: Optional[str] = None
    alert_name: Optional[str] = None
    severity: Optional[str] = "high"
    start_time: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize enclave on startup"""
    enclave.startup_checks()
    print("✓ PostMortemIQ API ready")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PostMortemIQ",
        "version": "1.0.0",
        "description": "GraphRAG Incident Root-Cause Engine with TEE"
    }


@app.get("/health")
async def health():
    """Health check endpoint with metrics"""
    enclave_status = enclave.get_status()
    dedup_stats = deduplicator.get_stats()
    cache_statistics = cache_stats()
    
    return {
        "status": "ok",
        "enclave": enclave_status,
        "cache_hit_rate": cache_statistics.get("hit_rate_pct", 0),
        "dedup_rate": dedup_stats.get("dedup_rate_pct", 0)
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint"""
    dedup_statistics = deduplicator.get_stats()
    cache_statistics = cache_stats()
    
    # Update metrics
    metrics["duplicates_blocked"] = dedup_statistics.get("duplicates_blocked", 0)
    metrics["cache_hits_total"] = cache_statistics.get("hits", 0)
    
    # Format as Prometheus plaintext
    lines = [
        "# HELP postmortemiq_alerts_total Total number of alerts processed",
        "# TYPE postmortemiq_alerts_total counter",
        f"postmortemiq_alerts_total {metrics['alerts_total']}",
        "",
        "# HELP postmortemiq_duplicates_blocked Number of duplicate alerts blocked",
        "# TYPE postmortemiq_duplicates_blocked counter",
        f"postmortemiq_duplicates_blocked {metrics['duplicates_blocked']}",
        "",
        "# HELP postmortemiq_llm_calls_total Total number of LLM API calls",
        "# TYPE postmortemiq_llm_calls_total counter",
        f"postmortemiq_llm_calls_total {metrics['llm_calls_total']}",
        "",
        "# HELP postmortemiq_cache_hits_total Total number of cache hits",
        "# TYPE postmortemiq_cache_hits_total counter",
        f"postmortemiq_cache_hits_total {metrics['cache_hits_total']}",
        "",
        "# HELP postmortemiq_avg_tokens_saved Average tokens saved per query",
        "# TYPE postmortemiq_avg_tokens_saved gauge",
        f"postmortemiq_avg_tokens_saved {metrics['avg_tokens_saved']}",
    ]
    
    return PlainTextResponse("\n".join(lines))


@app.get("/attest")
async def attest():
    """Attestation endpoint"""
    report = enclave.get_attestation_report()
    return report


async def process_incident_task(task_id: str, request: IncidentRequest):
    """Background task to process incident"""
    try:
        # Update status to processing
        store_task(task_id, {"status": "processing", "incident_id": request.incident_id})
        
        incident_data = {
            "incident_id": request.incident_id,
            "alert_id": request.alert_id or f"alert_{request.incident_id.split('_')[1] if '_' in request.incident_id else '1'}",
            "alert_name": request.alert_name or "Unknown alert",
            "severity": request.severity,
            "start_time": request.start_time or "2024-01-15T14:33:00Z",
            "service": request.alert_name or "unknown",
            "error_type": request.severity,
            "component": request.alert_id or request.incident_id
        }
        
        # Check for duplicates
        if deduplicator.is_duplicate(incident_data):
            result = {
                "status": "duplicate",
                "incident_id": request.incident_id,
                "message": "Alert is a duplicate within the deduplication window",
                "dedup_stats": deduplicator.get_stats()
            }
            store_task(task_id, {"status": "completed", "result": result})
            return
        
        # Update metrics
        metrics["alerts_total"] += 1
        
        # Run both pipelines in parallel
        baseline_task = asyncio.create_task(
            asyncio.to_thread(baseline_pipeline.run, request.incident_id, incident_data)
        )
        graphrag_task = asyncio.create_task(
            asyncio.to_thread(graphrag_pipeline.run, request.incident_id, incident_data)
        )
        
        baseline_result, graphrag_result = await asyncio.gather(baseline_task, graphrag_task)
        
        # Update LLM calls metric
        metrics["llm_calls_total"] += 2
        
        # Calculate tokens saved
        tokens_saved = baseline_result.get("total_tokens", 0) - graphrag_result.get("total_tokens", 0)
        metrics["avg_tokens_saved"] = tokens_saved
        
        # Load ground truth if available
        ground_truth = None
        try:
            with open("data/synthetic_incidents.json", 'r') as f:
                data = json.load(f)
                for incident in data.get("incidents", []):
                    if incident["incident_id"] == request.incident_id:
                        ground_truth = incident
                        break
        except Exception:
            pass
        
        # Compare results
        comparison = comparator.compare(baseline_result, graphrag_result, ground_truth)
        
        # Store completed result
        store_task(task_id, {"status": "completed", "result": comparison})
        
    except Exception as e:
        # Store error
        store_task(task_id, {"status": "error", "error": str(e)})


@app.post("/analyze")
async def analyze_incident_async(request: IncidentRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Analyze incident asynchronously (returns immediately with task_id)
    
    Args:
        request: Incident information
        background_tasks: FastAPI background tasks
        
    Returns:
        Task ID and status
    """
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Store initial status
    store_task(task_id, {"status": "queued", "incident_id": request.incident_id})
    
    # Add to background tasks
    background_tasks.add_task(process_incident_task, task_id, request)
    
    return {
        "task_id": task_id,
        "status": "queued",
        "incident_id": request.incident_id
    }


@app.get("/result/{task_id}")
async def get_result(task_id: str) -> Dict[str, Any]:
    """
    Get result of async analysis task
    
    Args:
        task_id: Task identifier
        
    Returns:
        Task result or status
    """
    task_data = get_task(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_data


@app.post("/analyze/sync")
async def analyze_incident_sync(request: IncidentRequest) -> Dict[str, Any]:
    """
    Analyze incident synchronously (backward compatibility)
    
    Args:
        request: Incident information
        
    Returns:
        Comparison result
    """
    incident_data = {
        "incident_id": request.incident_id,
        "alert_id": request.alert_id or f"alert_{request.incident_id.split('_')[1] if '_' in request.incident_id else '1'}",
        "alert_name": request.alert_name or "Unknown alert",
        "severity": request.severity,
        "start_time": request.start_time or "2024-01-15T14:33:00Z",
        "service": request.alert_name or "unknown",
        "error_type": request.severity,
        "component": request.alert_id or request.incident_id
    }
    
    # Check for duplicates
    if deduplicator.is_duplicate(incident_data):
        import logging
        logging.warning(
            f"Duplicate alert blocked: {request.incident_id} "
            f"(fingerprint: {deduplicator.generate_fingerprint(incident_data)})"
        )
        return {
            "status": "duplicate",
            "incident_id": request.incident_id,
            "message": "Alert is a duplicate within the deduplication window",
            "dedup_stats": deduplicator.get_stats()
        }
    
    # Update metrics
    metrics["alerts_total"] += 1
    
    # Run both pipelines in parallel
    baseline_task = asyncio.create_task(
        asyncio.to_thread(baseline_pipeline.run, request.incident_id, incident_data)
    )
    graphrag_task = asyncio.create_task(
        asyncio.to_thread(graphrag_pipeline.run, request.incident_id, incident_data)
    )
    
    baseline_result, graphrag_result = await asyncio.gather(baseline_task, graphrag_task)
    
    # Update metrics
    metrics["llm_calls_total"] += 2
    tokens_saved = baseline_result.get("total_tokens", 0) - graphrag_result.get("total_tokens", 0)
    metrics["avg_tokens_saved"] = tokens_saved
    
    # Load ground truth if available
    ground_truth = None
    try:
        with open("data/synthetic_incidents.json", 'r') as f:
            data = json.load(f)
            for incident in data.get("incidents", []):
                if incident["incident_id"] == request.incident_id:
                    ground_truth = incident
                    break
    except Exception:
        pass
    
    # Compare results
    comparison = comparator.compare(baseline_result, graphrag_result, ground_truth)
    
    return comparison


@app.post("/incident")
async def analyze_incident_legacy(request: IncidentRequest) -> Dict[str, Any]:
    """Legacy endpoint - redirects to sync analysis"""
    return await analyze_incident_sync(request)


@app.get("/benchmark")
async def run_benchmark() -> Dict[str, Any]:
    """
    Run benchmark across all synthetic incidents
    
    Returns:
        Aggregate benchmark results
    """
    try:
        with open("data/synthetic_incidents.json", 'r') as f:
            data = json.load(f)
            incidents = data.get("incidents", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load incidents: {e}")
    
    if not incidents:
        raise HTTPException(status_code=404, detail="No incidents found")
    
    # Run all incidents (limit to first 10 for demo)
    comparisons = []
    for incident in incidents[:10]:
        incident_data = {
            "incident_id": incident["incident_id"],
            "alert_id": incident["alert_id"],
            "alert_name": incident["alert_name"],
            "severity": incident["severity"],
            "start_time": incident["start_time"]
        }
        
        # Run both pipelines
        baseline_result = baseline_pipeline.run(incident["incident_id"], incident_data)
        graphrag_result = graphrag_pipeline.run(incident["incident_id"], incident_data)
        
        # Compare
        comparison = comparator.compare(baseline_result, graphrag_result, incident)
        comparisons.append(comparison)
    
    # Aggregate results
    aggregate = comparator.aggregate_results(comparisons)
    
    return {
        "benchmark_results": aggregate,
        "individual_results": comparisons
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
