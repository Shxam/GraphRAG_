"""
LLM-Only Pipeline for PostMortemIQ
Processes incidents with raw alert JSON only - no retrieval, no graph traversal
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from typing import Dict, Any
from llm.groq_client import GroqClient


class LLMOnlyPipeline:
    """LLM-Only pipeline using raw alert JSON with no retrieval"""
    
    def __init__(self):
        self.llm_client = GroqClient()
    
    def build_prompt(self, incident_data: Dict[str, Any]) -> str:
        """
        Build minimal prompt from raw alert JSON only
        
        Args:
            incident_data: Raw incident information
            
        Returns:
            Prompt string
        """
        prompt = f"""You are an expert SRE analyzing a production incident. Based ONLY on the alert information below, provide a root cause analysis.

ALERT INFORMATION:
{json.dumps(incident_data, indent=2)}

Provide a concise, 1-2 sentence paragraph summarizing:
- The most likely root cause
- The affected services
- The resolution
Do NOT use lists or bullet points. Output ONLY the concise summary. If there is insufficient information, state that clearly rather than speculating.
"""
        return prompt
    
    def run(self, incident_id: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run LLM-Only pipeline on an incident
        
        Args:
            incident_id: The incident identifier
            incident_data: Raw incident information
            
        Returns:
            Pipeline result with RCA, tokens, latency, cost
        """
        start_time = time.time()
        
        # Build minimal prompt from raw alert JSON
        prompt = self.build_prompt(incident_data)
        
        # Call LLM with retry logic
        llm_result = self.llm_client.call_llm(prompt)
        
        # Calculate cost using mixtral-8x7b pricing
        # $0.0008/1K tokens for both input and output
        cost = self.llm_client.calculate_cost(
            llm_result["input_tokens"],
            llm_result["output_tokens"],
            input_price_per_1k=0.0008,
            output_price_per_1k=0.0008
        )
        
        total_latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "pipeline": "llm_only",
            "incident_id": incident_id,
            "rca_report": llm_result["response"],
            "prompt_tokens": llm_result["input_tokens"],
            "completion_tokens": llm_result["output_tokens"],
            "total_tokens": llm_result["total_tokens"],
            "latency_ms": total_latency_ms,
            "llm_latency_ms": llm_result["latency_ms"],
            "cost_usd": cost,
            "context_type": "raw_alert_only"
        }


if __name__ == "__main__":
    pipeline = LLMOnlyPipeline()
    
    test_incident = {
        "incident_id": "incident_1",
        "alert_id": "alert_1",
        "alert_name": "High error rate in auth-svc",
        "severity": "critical",
        "start_time": "2024-01-15T14:33:00Z"
    }
    
    result = pipeline.run("incident_1", test_incident)
    print(f"LLM-Only Pipeline Result:")
    print(f"  Tokens: {result['total_tokens']}")
    print(f"  Latency: {result['latency_ms']}ms")
    print(f"  Cost: ${result['cost_usd']:.6f}")
    print(f"  Response: {result['rca_report'][:200]}...")
