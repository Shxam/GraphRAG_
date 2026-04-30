"""
Baseline LLM Pipeline for PostMortemIQ
Processes incidents with full raw context (no graph traversal)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any
from llm.prompt_builder import PromptBuilder
from llm.groq_client import GroqClient


class BaselinePipeline:
    """Baseline pipeline using full raw context"""
    
    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm_client = GroqClient()
    
    def assemble_context(self, incident_id: str, incident_data: Dict[str, Any]) -> str:
        """
        Assemble full raw context from incident data
        Target: >8000 tokens
        
        Args:
            incident_id: The incident identifier
            incident_data: Complete incident information
            
        Returns:
            Full context string
        """
        context_parts = []
        
        # Alert information (~500 tokens)
        context_parts.append("=== ALERT INFORMATION ===")
        context_parts.append(f"Alert ID: {incident_data.get('alert_id', 'N/A')}")
        context_parts.append(f"Alert Name: {incident_data.get('alert_name', 'N/A')}")
        context_parts.append(f"Severity: {incident_data.get('severity', 'N/A')}")
        context_parts.append(f"Start Time: {incident_data.get('start_time', 'N/A')}")
        context_parts.append("")
        
        # Mock log excerpts (~3000 tokens)
        context_parts.append("=== LOG EXCERPTS ===")
        context_parts.append(self._generate_mock_logs(3000))
        context_parts.append("")
        
        # Deployment notes (~2000 tokens)
        context_parts.append("=== RECENT DEPLOYMENTS ===")
        context_parts.append(self._generate_deployment_notes(2000))
        context_parts.append("")
        
        # Config history (~1500 tokens)
        context_parts.append("=== CONFIGURATION CHANGES ===")
        context_parts.append(self._generate_config_history(1500))
        context_parts.append("")
        
        # Service dependency docs (~2000 tokens)
        context_parts.append("=== SERVICE DEPENDENCIES ===")
        context_parts.append(self._generate_dependency_docs(2000))
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _generate_mock_logs(self, target_tokens: int) -> str:
        """Generate mock log entries to reach target token count"""
        log_template = """[2024-01-15 14:33:22] ERROR auth-svc: JWT validation failed for user_id=12345
[2024-01-15 14:33:23] WARN payment-svc: Upstream auth service returned 401
[2024-01-15 14:33:24] ERROR api-gateway: Authentication middleware timeout
[2024-01-15 14:33:25] INFO user-svc: Retrying auth request (attempt 2/3)
[2024-01-15 14:33:26] ERROR auth-svc: Token expiry check failed: expected 3600s, got 60s
"""
        # Repeat to reach target
        repeats = (target_tokens * 4) // len(log_template)
        return (log_template * repeats)[:target_tokens * 4]
    
    def _generate_deployment_notes(self, target_tokens: int) -> str:
        """Generate mock deployment notes"""
        notes = """Deployment v2.4.1 to auth-svc at 14:32 UTC
- Updated JWT configuration
- Changed token expiry settings
- Modified authentication middleware
- Updated dependency versions
- Deployed to production cluster
- Health checks passed
- Rollout completed successfully

Deployment v2.4.0 to payment-svc at 12:15 UTC
- Updated payment processing logic
- Added new fraud detection rules
- Modified database queries
- Updated API endpoints
"""
        repeats = (target_tokens * 4) // len(notes)
        return (notes * repeats)[:target_tokens * 4]
    
    def _generate_config_history(self, target_tokens: int) -> str:
        """Generate mock config change history"""
        config = """Config change: JWT_EXPIRY_SECONDS
- Previous value: 3600
- New value: 60
- Changed by: deploy-bot
- Timestamp: 2024-01-15 14:32:00
- Deployment: v2.4.1
- Service: auth-svc

Config change: MAX_CONNECTIONS
- Previous value: 1000
- New value: 2000
- Changed by: ops-team
- Timestamp: 2024-01-15 10:00:00
"""
        repeats = (target_tokens * 4) // len(config)
        return (config * repeats)[:target_tokens * 4]
    
    def _generate_dependency_docs(self, target_tokens: int) -> str:
        """Generate mock dependency documentation"""
        docs = """Service: auth-svc
Dependencies:
- payment-svc (calls auth-svc for token validation)
- api-gateway (routes through auth-svc)
- user-svc (depends on auth-svc for authentication)
- order-svc (indirect dependency via payment-svc)

Service: payment-svc
Dependencies:
- auth-svc (authentication)
- billing-svc (payment processing)
- notification-svc (payment confirmations)
"""
        repeats = (target_tokens * 4) // len(docs)
        return (docs * repeats)[:target_tokens * 4]
    
    def run(self, incident_id: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run baseline pipeline on an incident
        
        Args:
            incident_id: The incident identifier
            incident_data: Complete incident information
            
        Returns:
            Pipeline result with RCA, tokens, latency, cost
        """
        # Assemble full context
        context = self.assemble_context(incident_id, incident_data)
        
        # Build prompt
        prompt = self.prompt_builder.build_baseline_prompt(context, incident_id)
        
        # Call LLM
        llm_result = self.llm_client.call_llm(prompt)
        
        # Calculate cost
        cost = self.llm_client.calculate_cost(
            llm_result["input_tokens"],
            llm_result["output_tokens"]
        )
        
        return {
            "pipeline": "baseline",
            "incident_id": incident_id,
            "rca_report": llm_result["response"],
            "input_tokens": llm_result["input_tokens"],
            "output_tokens": llm_result["output_tokens"],
            "total_tokens": llm_result["total_tokens"],
            "latency_ms": llm_result["latency_ms"],
            "cost_usd": cost,
            "context_size": len(context)
        }


if __name__ == "__main__":
    pipeline = BaselinePipeline()
    
    test_incident = {
        "incident_id": "incident_1",
        "alert_id": "alert_1",
        "alert_name": "High error rate in auth-svc",
        "severity": "critical",
        "start_time": "2024-01-15T14:33:00Z"
    }
    
    result = pipeline.run("incident_1", test_incident)
    print(f"Baseline Pipeline Result:")
    print(f"  Tokens: {result['total_tokens']}")
    print(f"  Latency: {result['latency_ms']}ms")
    print(f"  Cost: ${result['cost_usd']:.6f}")
    print(f"  Context size: {result['context_size']} chars")
