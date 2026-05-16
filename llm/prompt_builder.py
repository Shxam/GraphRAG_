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
        # NOTE: Do NOT sanitize context here — it is system-generated content,
        # not user input. sanitize_alert_text() hard-caps at 2000 chars which
        # would destroy the baseline's intentionally large context (~25,000 chars).
        
        system_prompt = """You are an expert Site Reliability Engineer analyzing a production incident.
Your task is to identify the root cause based on the provided logs, alerts, and system information.
Be specific about what caused the incident and which services are affected."""
        
        user_prompt = f"""Analyze this production incident and identify the root cause:

{context}

Please provide a concise, 1-2 sentence paragraph summarizing:
- The exact root cause
- The affected services
- The resolution
Do NOT use lists or bullet points. Output ONLY the concise summary."""
        
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

Based on this verified causal chain, provide a concise, 1-2 sentence paragraph summarizing:
- The exact root cause (which Deployment or ConfigChange caused the incident)
- The affected services
- The resolution
Do NOT use lists or bullet points. Output ONLY the concise summary."""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    @staticmethod
    def _format_subgraph(subgraph: Dict[str, Any], alert_id: str = "unknown") -> str:
        """Format subgraph into readable text context with name resolution"""
        lines = ["CAUSAL GRAPH:"]
        lines.append("")
        
        # Build id-to-name lookup for resolving edge references
        id_to_name = {}
        
        node_types = {}
        node_names = {}  # id -> name mapping
        for node in subgraph.get("nodes", []):
            n_id = node.get("id", node.get("team_id", node.get("service_id", "")))
            node_types[n_id] = node.get("type", "Unknown")
            node_names[n_id] = node.get("name", "")
            
        # Extract services that actually appear in edges (FIX HALLUCINATION)
        # Collect both IDs and NAMES so we can match affected_services by either
        services_in_edges_ids = set()
        services_in_edges_names = set()
        for edge in subgraph.get("edges", []):
            from_id = edge.get("from", "")
            to_id = edge.get("to", "")
            
            if node_types.get(from_id) == "Service":
                services_in_edges_ids.add(from_id)
                if node_names.get(from_id):
                    services_in_edges_names.add(node_names[from_id])
            if node_types.get(to_id) == "Service":
                services_in_edges_ids.add(to_id)
                if node_names.get(to_id):
                    services_in_edges_names.add(node_names[to_id])
        
        # Filter affected_services to only include services in edges
        original_affected = subgraph.get("affected_services", [])
        filtered_affected = []
        
        for svc in original_affected:
            if isinstance(svc, dict):
                svc_id = svc.get("service_id", svc.get("id", ""))
                svc_name = svc.get("name", "")
                if svc_id in services_in_edges_ids or svc_name in services_in_edges_names:
                    filtered_affected.append(svc)
            elif isinstance(svc, str):
                if svc in services_in_edges_ids or svc in services_in_edges_names:
                    filtered_affected.append(svc)
        
        # If filtering removed everything, keep originals (safety fallback)
        if not filtered_affected and original_affected:
            filtered_affected = original_affected
        
        # Update subgraph with filtered list (prevents hallucination)
        if len(filtered_affected) != len(original_affected):
            logger.info(f"Filtered affected_services from {len(original_affected)} to {len(filtered_affected)} (only services in graph edges)")
            subgraph["affected_services"] = filtered_affected
        
        # Format nodes
        lines.append("Nodes:")
        for node in subgraph.get("nodes", []):
            node_type = node.get("type", "Unknown")
            node_id = node.get("id", node.get("team_id", node.get("service_id", "")))
            node_name = PromptBuilder.sanitize_alert_text(node.get("name", ""), alert_id)
            
            if node_type == "ConfigChange":
                key = PromptBuilder.sanitize_alert_text(node.get('key', ''), alert_id)
                old_val = PromptBuilder.sanitize_alert_text(str(node.get('old_value', '')), alert_id)
                new_val = PromptBuilder.sanitize_alert_text(str(node.get('new_value', '')), alert_id)
                display_name = f"{key} changed from {old_val} to {new_val}"
                lines.append(f"  - {node_type}: {display_name}")
                id_to_name[node_id] = f"Config({key}: {old_val}->{new_val})"
            elif node_type == "Deployment":
                version = PromptBuilder.sanitize_alert_text(node.get('version', ''), alert_id)
                lines.append(f"  - {node_type}: version {version}")
                id_to_name[node_id] = f"Deployment {version}"
            elif node_type == "Team":
                lines.append(f"  - {node_type}: {node_name}")
                id_to_name[node_id] = f"{node_name} Team"
            else:
                lines.append(f"  - {node_type}: {node_name}")
                id_to_name[node_id] = node_name or node_id
        
        lines.append("")
        
        # Format edges using resolved names
        lines.append("Relationships:")
        for edge in subgraph.get("edges", []):
            from_id = edge.get('from', '')
            to_id = edge.get('to', '')
            edge_type = PromptBuilder.sanitize_alert_text(edge.get('type', ''), alert_id)
            from_name = id_to_name.get(from_id, from_id)
            to_name = id_to_name.get(to_id, to_id)
            lines.append(f"  - {from_name} --[{edge_type}]--> {to_name}")
        
        lines.append("")
        
        # Add filtered affected services (only those in graph)
        if filtered_affected:
            lines.append("Affected Services (verified in graph):")
            for svc in filtered_affected:
                svc_id = svc.get("service_id", svc.get("name", "")) if isinstance(svc, dict) else svc
                svc_name = id_to_name.get(svc_id, svc_id)
                lines.append(f"  - {svc_name}")
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
    def build_rag_prompt(context: str, alert_id: str = "unknown", incident_data: Dict[str, Any] = None) -> str:
        """
        Build prompt for Basic RAG pipeline with retrieved chunks
        
        Args:
            context: Retrieved chunks from vector similarity search
            alert_id: Alert ID for logging
            incident_data: Incident information
            
        Returns:
            Complete prompt string
        """
        # Sanitize context
        context = PromptBuilder.sanitize_alert_text(context, alert_id)
        
        system_prompt = """You are an expert Site Reliability Engineer analyzing a production incident.
You have been provided with relevant information retrieved from past incidents and documentation.
Use this information to identify the root cause and provide remediation guidance."""
        
        incident_info = ""
        if incident_data:
            alert_name = PromptBuilder.sanitize_alert_text(incident_data.get('alert_name', 'Unknown'), alert_id)
            severity = PromptBuilder.sanitize_alert_text(incident_data.get('severity', 'unknown'), alert_id)
            incident_info = f"\nCurrent Incident: {alert_name} (Severity: {severity})\n"
        
        user_prompt = f"""Analyze this production incident using the retrieved information:
{incident_info}
RETRIEVED CONTEXT:
{context}

Based on the retrieved information, provide a concise, 1-2 sentence paragraph summarizing:
- The exact root cause
- The affected services
- The resolution
Do NOT use lists or bullet points. Output ONLY the concise summary."""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
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
