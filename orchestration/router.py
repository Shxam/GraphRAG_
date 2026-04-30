"""
Incident Router and Orchestration Layer
FastAPI service that routes incidents through both pipelines
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from pipelines.baseline import BaselinePipeline
from pipelines.graphrag import GraphRAGPipeline
from pipelines.comparator import Comparator
from tee.enclave_runner import EnclaveRunner
from orchestration.deduplicator import AlertDeduplicator


app = FastAPI(title="PostMortemIQ API", version="1.0.0")

# Initialize components
enclave = EnclaveRunner()
baseline_pipeline = BaselinePipeline()
graphrag_pipeline = GraphRAGPipeline()
comparator = Comparator()
deduplicator = AlertDeduplicator(window_seconds=300)


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
    """Health check endpoint"""
    enclave_status = enclave.get_status()
    return {
        "status": "healthy",
        "enclave": enclave_status
    }


@app.get("/attest")
async def attest():
    """Attestation endpoint"""
    report = enclave.get_attestation_report()
    return report


@app.post("/incident")
async def analyze_incident(request: IncidentRequest) -> Dict[str, Any]:
    """
    Analyze incident using both pipelines
    
    Args:
        request: Incident information
        
    Returns:
        Comparison result
    """
    incident_data = {
        "incident_id": request.incident_id,
        "alert_id": request.alert_id or f"alert_{request.incident_id.split('_')[1]}",
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
    
    # Run both pipelines in parallel
    baseline_task = asyncio.create_task(
        asyncio.to_thread(baseline_pipeline.run, request.incident_id, incident_data)
    )
    graphrag_task = asyncio.create_task(
        asyncio.to_thread(graphrag_pipeline.run, request.incident_id, incident_data)
    )
    
    baseline_result, graphrag_result = await asyncio.gather(baseline_task, graphrag_task)
    
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
