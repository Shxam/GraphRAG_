"""
LLM Prompt Builder for PostMortemIQ
Constructs prompts for baseline and GraphRAG pipelines with input sanitization
"""

from typing import Dict, List, Any
import re
import logging

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builds LLM prompts for incident analysis with security"""
    
    @staticmethod
    def sanitize_alert_text(text: str, alert_id: str = "unknown") -> str:
        """
        Sanitize user-supplied text to prevent prompt injection
        
        Args:
            text: Text to sanitize
            alert_id: Alert ID for logging
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        original_text = text
        
        # Patterns to detect and redact (case-insensitive)
        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"you\s+are\s+now",
            r"</system>",
            r"\[INST\]",
            r"###",
            r"SYSTEM:",
            r"Assistant:",
            r"<\|im_start\|>",
            r"<\|im_end\|>",
            r"<\|endoftext\|>",
        ]
        
        # Check for injection attempts
        found_patterns = []
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found_patterns.append(pattern)
                text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
        
        # Hard cap at 2000 characters
        if len(text) > 2000:
            text = text[:2000]
            found_patterns.append("length_exceeded")
        
        # Log warning if any patterns were found
        if found_patterns:
            logger.warning(
                f"Prompt injection attempt detected in alert {alert_id}. "
                f"Patterns found: {', '.join(found_patterns)}"
            )
        
        return text
    
    @staticmethod
    def build_baseline_prompt(context: str, alert_id: str = "unknown") -> str:
        """
        Build prompt for baseline LLM pipeline with full raw context
        
        Args:
            context: Full raw context (logs, alerts, configs, etc.)
            alert_id: Alert ID for logging
            
        Returns:
            Complete prompt string
        """
        # Sanitize context
        context = PromptBuilder.sanitize_alert_text(context, alert_id)
        
        system_prompt = """You are an expert Site Reliability Engineer analyzing a production incident.
Your task is to identify the root cause based on the provided logs, alerts, and system information.
Be specific about what caused the incident and which services are affected."""
        
        user_prompt = f"""Analyze this production incident and identify the root cause:

{context}

Please provide:
1. Root cause identification
2. Affected services
3. Teams that should be paged
4. Recommended remediation steps"""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    @staticmethod
    def build_graphrag_prompt(subgraph: Dict[str, Any], similar_incidents: list = None, alert_id: str = "unknown") -> str:
        """
        Build prompt for GraphRAG pipeline with minimal subgraph context
        
        Args:
            subgraph: Causal subgraph from TigerGraph traversal
            similar_incidents: List of similar past incidents (optional)
            alert_id: Alert ID for logging
            
        Returns:
            Complete prompt string
        """
        system_prompt = """You are an expert Site Reliability Engineer analyzing a production incident.
You have been provided with a verified causal graph subgraph showing the relationships between
alerts, services, deployments, and configuration changes.

IMPORTANT: Only reason about entities and relationships present in the provided graph.
Do not invent or assume relationships that are not explicitly shown."""
        
        # Format subgraph as structured context (with sanitization)
        graph_context = PromptBuilder._format_subgraph(subgraph, alert_id)
        
        # Add similar incidents if available and high similarity
        similar_context = ""
        if similar_incidents:
            high_similarity = [inc for inc in similar_incidents if inc.get("similarity_score", 0) > 0.6]
            if high_similarity:
                similar_context = "\n\nSIMILAR PAST INCIDENTS:\n"
                for inc in high_similarity:
                    # Sanitize similar incident data
                    root_cause = PromptBuilder.sanitize_alert_text(inc.get('root_cause', ''), alert_id)
                    resolution = PromptBuilder.sanitize_alert_text(inc.get('resolution_summary', ''), alert_id)
                    
                    similar_context += f"\n- {inc['timestamp'][:10]} | Similarity: {inc['similarity_score']:.0%} | MTTR: {inc['mttr_minutes']}min\n"
                    similar_context += f"  Root Cause: {root_cause}\n"
                    similar_context += f"  Resolution: {resolution}\n"
        
        user_prompt = f"""Analyze this incident using the causal graph:

{graph_context}{similar_context}

Based on this verified causal chain, provide:
1. Root cause (which ConfigChange caused the incident)
2. Affected services (from the graph traversal)
3. Teams that should be paged (teams owning affected services)
4. Recommended remediation"""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    @staticmethod
    def _format_subgraph(subgraph: Dict[str, Any], alert_id: str = "unknown") -> str:
        """Format subgraph into readable text context with sanitization"""
        lines = ["CAUSAL GRAPH:"]
        lines.append("")
        
        # Format nodes
        lines.append("Nodes:")
        for node in subgraph.get("nodes", []):
            node_type = node.get("type", "Unknown")
            node_id = node.get("id", "")
            node_name = PromptBuilder.sanitize_alert_text(node.get("name", ""), alert_id)
            
            if node_type == "ConfigChange":
                key = PromptBuilder.sanitize_alert_text(node.get('key', ''), alert_id)
                old_val = PromptBuilder.sanitize_alert_text(str(node.get('old_value', '')), alert_id)
                new_val = PromptBuilder.sanitize_alert_text(str(node.get('new_value', '')), alert_id)
                lines.append(f"  - {node_type} {node_id}: {key} changed from {old_val} to {new_val}")
            elif node_type == "Deployment":
                version = PromptBuilder.sanitize_alert_text(node.get('version', ''), alert_id)
                lines.append(f"  - {node_type} {node_id}: version {version}")
            else:
                lines.append(f"  - {node_type} {node_id}: {node_name}")
        
        lines.append("")
        
        # Format edges
        lines.append("Relationships:")
        for edge in subgraph.get("edges", []):
            edge_from = PromptBuilder.sanitize_alert_text(edge.get('from', ''), alert_id)
            edge_to = PromptBuilder.sanitize_alert_text(edge.get('to', ''), alert_id)
            edge_type = PromptBuilder.sanitize_alert_text(edge.get('type', ''), alert_id)
            lines.append(f"  - {edge_from} --[{edge_type}]--> {edge_to}")
        
        lines.append("")
        
        # Add unpaged teams
        if subgraph.get("unpaged_teams"):
            lines.append("Teams NOT YET PAGED:")
            for team in subgraph["unpaged_teams"]:
                team_name = PromptBuilder.sanitize_alert_text(team.get('name', ''), alert_id)
                reason = PromptBuilder.sanitize_alert_text(team.get('reason', ''), alert_id)
                lines.append(f"  - {team_name}: {reason}")
        
        return "\n".join(lines)
    
    @staticmethod
    def count_tokens_estimate(text: str) -> int:
        """
        Rough token count estimate (4 chars ≈ 1 token)
        For accurate counting, use tiktoken in production
        """
        return len(text) // 4


if __name__ == "__main__":
    # Test prompt building
    builder = PromptBuilder()
    
    # Test baseline prompt
    baseline_context = "Alert: High error rate in auth-svc\nLogs: [8000 tokens of logs here]..."
    baseline_prompt = builder.build_baseline_prompt(baseline_context)
    print(f"Baseline prompt tokens (estimate): {builder.count_tokens_estimate(baseline_prompt)}")
    
    # Test GraphRAG prompt
    subgraph = {
        "nodes": [
            {"type": "Alert", "id": "alert_1", "name": "High error rate"},
            {"type": "Service", "id": "svc_1", "name": "auth-svc"},
            {"type": "ConfigChange", "id": "config_3", "key": "JWT_EXPIRY_SECONDS", 
             "old_value": "3600", "new_value": "60"}
        ],
        "edges": [
            {"from": "alert_1", "to": "svc_1", "type": "fired_on"},
            {"from": "svc_1", "to": "config_3", "type": "changed_config"}
        ],
        "unpaged_teams": [
            {"name": "Payments", "reason": "Owns affected service"}
        ]
    }
    graphrag_prompt = builder.build_graphrag_prompt(subgraph)
    print(f"GraphRAG prompt tokens (estimate): {builder.count_tokens_estimate(graphrag_prompt)}")
    print(f"\nGraphRAG prompt:\n{graphrag_prompt}")
