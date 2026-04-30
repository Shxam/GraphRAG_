"""
GraphRAG Pipeline for PostMortemIQ
Processes incidents using TigerGraph traversal + minimal LLM context
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any
from graph.queries import GraphQueries
from llm.prompt_builder import PromptBuilder
from llm.groq_client import GroqClient
from llm.response_verifier import ResponseVerifier
from graph.query_cache import cached_gsql
from pipelines.runbook_generator import RunbookGenerator
import hashlib


class GraphRAGPipeline:
    """GraphRAG pipeline using graph traversal + LLM"""
    
    def __init__(self):
        self.graph_queries = GraphQueries()
        self.prompt_builder = PromptBuilder()
        self.llm_client = GroqClient()
        self.verifier = ResponseVerifier()
        self.runbook_generator = RunbookGenerator()
    
    def run(self, incident_id: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run GraphRAG pipeline on an incident
        
        Args:
            incident_id: The incident identifier
            incident_data: Incident information
            
        Returns:
            Pipeline result with RCA, tokens, latency, cost, hallucinations
        """
        import time
        start_time = time.time()
        
        # Generate cache key from alert fingerprint
        fingerprint_str = f"{incident_data.get('service', 'unknown')}:{incident_data.get('severity', 'unknown')}:{incident_id}"
        alert_fingerprint = hashlib.md5(fingerprint_str.encode()).hexdigest()
        cache_key = f"graphrag:subgraph:{alert_fingerprint}"
        
        # Step 1: Get causal subgraph from TigerGraph (with caching)
        def fetch_subgraph():
            return self.graph_queries.get_causal_subgraph(incident_id)
        
        subgraph = cached_gsql(cache_key, fetch_subgraph, ttl=300)
        graph_latency_ms = int((time.time() - start_time) * 1000)
        
        # Step 1.5: Find similar past incidents
        similar_incidents = self.graph_queries.find_similar_incidents(alert_fingerprint, top_k=5)
        
        # Step 2: Build minimal prompt from subgraph
        prompt = self.prompt_builder.build_graphrag_prompt(subgraph, similar_incidents, incident_id)
        
        # Step 3: Call LLM with minimal context
        llm_result = self.llm_client.call_llm(prompt)
        
        # Step 4: Verify response for hallucinations
        hallucination_report = self.verifier.detect_hallucinations(
            llm_result["response"],
            subgraph
        )
        
        # Calculate cost
        cost = self.llm_client.calculate_cost(
            llm_result["input_tokens"],
            llm_result["output_tokens"]
        )
        
        total_latency_ms = graph_latency_ms + llm_result["latency_ms"]
        
        # Step 5: Generate runbook
        alert_with_fingerprint = {
            **incident_data,
            "fingerprint": alert_fingerprint
        }
        runbook_path = self.runbook_generator.generate_runbook(
            llm_result["response"],
            alert_with_fingerprint
        )
        
        return {
            "pipeline": "graphrag",
            "incident_id": incident_id,
            "rca_report": llm_result["response"],
            "input_tokens": llm_result["input_tokens"],
            "output_tokens": llm_result["output_tokens"],
            "total_tokens": llm_result["total_tokens"],
            "latency_ms": total_latency_ms,
            "graph_latency_ms": graph_latency_ms,
            "llm_latency_ms": llm_result["latency_ms"],
            "cost_usd": cost,
            "subgraph": subgraph,
            "similar_incidents": similar_incidents,
            "hallucination_count": hallucination_report["hallucination_count"],
            "hallucination_rate": hallucination_report["hallucination_rate"],
            "hallucinated_entities": hallucination_report["hallucinated_entities"],
            "runbook_path": runbook_path
        }


if __name__ == "__main__":
    pipeline = GraphRAGPipeline()
    
    test_incident = {
        "incident_id": "incident_1",
        "alert_id": "alert_1",
        "alert_name": "High error rate in auth-svc",
        "severity": "critical",
        "start_time": "2024-01-15T14:33:00Z"
    }
    
    result = pipeline.run("incident_1", test_incident)
    print(f"GraphRAG Pipeline Result:")
    print(f"  Tokens: {result['total_tokens']}")
    print(f"  Latency: {result['latency_ms']}ms (graph: {result['graph_latency_ms']}ms, llm: {result['llm_latency_ms']}ms)")
    print(f"  Cost: ${result['cost_usd']:.6f}")
    print(f"  Hallucinations: {result['hallucination_count']} ({result['hallucination_rate']:.1%})")
