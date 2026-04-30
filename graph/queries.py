"""
GSQL Query Wrappers for PostMortemIQ
Python interface to TigerGraph causal chain queries
"""

import pyTigerGraph as tg
import os
from dotenv import load_dotenv
from typing import Dict, List, Any

load_dotenv()


class GraphQueries:
    """Wrapper for GSQL traversal queries"""
    
    def __init__(self):
        self.conn = tg.TigerGraphConnection(
            host=os.getenv("TIGERGRAPH_HOST"),
            username=os.getenv("TIGERGRAPH_USERNAME"),
            password=os.getenv("TIGERGRAPH_PASSWORD"),
            graphname=os.getenv("TIGERGRAPH_GRAPH_NAME", "IncidentGraph")
        )
    
    def blast_radius(self, incident_id: str, max_hops: int = 4) -> Dict[str, Any]:
        """
        Find all services affected within N hops of the incident origin
        
        Args:
            incident_id: The incident identifier
            max_hops: Maximum traversal depth
            
        Returns:
            Dictionary with affected services and traversal path
        """
        # Simulated response for demo (replace with actual GSQL call)
        return {
            "affected_services": [
                {"service_id": "svc_1", "name": "auth-svc", "hop": 0},
                {"service_id": "svc_2", "name": "payment-svc", "hop": 1},
                {"service_id": "svc_3", "name": "api-gateway", "hop": 2}
            ],
            "total_affected": 3,
            "max_hops_reached": max_hops
        }
    
    def root_cause_chain(self, alert_id: str) -> Dict[str, Any]:
        """
        Trace backwards from alert to earliest causal ConfigChange
        
        Args:
            alert_id: The alert identifier
            
        Returns:
            Causal chain from alert to root cause
        """
        return {
            "alert_id": alert_id,
            "causal_chain": [
                {"type": "Alert", "id": alert_id, "name": "High error rate"},
                {"type": "Service", "id": "svc_1", "name": "auth-svc"},
                {"type": "Deployment", "id": "deploy_5", "version": "v2.4.1"},
                {"type": "ConfigChange", "id": "config_3", "key": "JWT_EXPIRY_SECONDS", 
                 "old_value": "3600", "new_value": "60"}
            ],
            "root_cause": "config_3",
            "confidence": 0.95
        }
    
    def unpaged_teams(self, incident_id: str) -> List[Dict[str, str]]:
        """
        Find teams owning affected services not yet paged
        
        Args:
            incident_id: The incident identifier
            
        Returns:
            List of teams that should be paged
        """
        return [
            {"team_id": "team_2", "name": "Payments", "reason": "Owns affected service payment-svc"},
            {"team_id": "team_3", "name": "API", "reason": "Owns affected service api-gateway"}
        ]
    
    def runbook_matcher(self, service_id: str, issue_type: str) -> Dict[str, Any]:
        """
        Find best matching runbook for the service and issue type
        
        Args:
            service_id: The service identifier
            issue_type: Type of issue (e.g., "auth-failure", "high-latency")
            
        Returns:
            Best matching runbook
        """
        return {
            "runbook_id": "runbook_1",
            "title": f"Fix {issue_type} in service",
            "url": "https://wiki.company.com/runbooks/1",
            "match_score": 0.87
        }
    
    def get_causal_subgraph(self, incident_id: str) -> Dict[str, Any]:
        """
        Get complete causal subgraph for an incident
        Combines blast_radius, root_cause_chain, and unpaged_teams
        
        Args:
            incident_id: The incident identifier
            
        Returns:
            Complete subgraph with nodes and edges
        """
        blast = self.blast_radius(incident_id)
        chain = self.root_cause_chain(f"alert_{incident_id.split('_')[1]}")
        teams = self.unpaged_teams(incident_id)
        
        return {
            "incident_id": incident_id,
            "nodes": chain["causal_chain"] + [{"type": "Team", **t} for t in teams],
            "edges": [
                {"from": "alert_1", "to": "svc_1", "type": "fired_on"},
                {"from": "svc_1", "to": "deploy_5", "type": "had_deployment"},
                {"from": "deploy_5", "to": "config_3", "type": "changed_config"},
                {"from": "svc_1", "to": "team_2", "type": "owned_by"}
            ],
            "affected_services": blast["affected_services"],
            "unpaged_teams": teams,
            "root_cause": chain["root_cause"]
        }
    
    def find_similar_incidents(self, alert_fingerprint: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar past incidents based on causal subgraph overlap
        
        Uses Jaccard similarity on edge sets to find incidents with similar causal patterns
        
        Args:
            alert_fingerprint: Fingerprint of current alert
            top_k: Number of similar incidents to return
            
        Returns:
            List of similar incidents with similarity scores
        """
        try:
            # In a real implementation, this would query TigerGraph for:
            # 1. Get edge set of current incident's subgraph
            # 2. Compare with edge sets of historical incidents
            # 3. Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|
            # 4. Return top_k most similar
            
            # For now, return synthetic similar incidents
            # This would be replaced with actual TigerGraph query
            pass
        except Exception as e:
            print(f"Error finding similar incidents: {e}")
        
        # Fallback: return hardcoded similar incidents
        from datetime import datetime, timedelta
        import random
        
        similar_incidents = [
            {
                "incident_id": "incident_hist_001",
                "similarity_score": 0.85,
                "mttr_minutes": 12,
                "resolution_summary": "Rolled back JWT_EXPIRY config change in auth-svc",
                "timestamp": (datetime.now() - timedelta(days=7)).isoformat(),
                "root_cause": "Config change: JWT_EXPIRY 3600→60"
            },
            {
                "incident_id": "incident_hist_002",
                "similarity_score": 0.72,
                "mttr_minutes": 18,
                "resolution_summary": "Reverted authentication timeout configuration",
                "timestamp": (datetime.now() - timedelta(days=14)).isoformat(),
                "root_cause": "Config change: AUTH_TIMEOUT 30→5"
            },
            {
                "incident_id": "incident_hist_003",
                "similarity_score": 0.68,
                "mttr_minutes": 25,
                "resolution_summary": "Fixed token validation logic after config update",
                "timestamp": (datetime.now() - timedelta(days=21)).isoformat(),
                "root_cause": "Code change: token validator"
            },
            {
                "incident_id": "incident_hist_004",
                "similarity_score": 0.61,
                "mttr_minutes": 15,
                "resolution_summary": "Increased session timeout to prevent premature expiry",
                "timestamp": (datetime.now() - timedelta(days=30)).isoformat(),
                "root_cause": "Config change: SESSION_TTL"
            },
            {
                "incident_id": "incident_hist_005",
                "similarity_score": 0.55,
                "mttr_minutes": 22,
                "resolution_summary": "Restarted auth service after config corruption",
                "timestamp": (datetime.now() - timedelta(days=45)).isoformat(),
                "root_cause": "Config corruption"
            }
        ]
        
        # Return top_k
        return similar_incidents[:top_k]


if __name__ == "__main__":
    queries = GraphQueries()
    
    # Test queries
    print("Testing blast_radius...")
    result = queries.blast_radius("incident_1", max_hops=4)
    print(f"Found {result['total_affected']} affected services")
    
    print("\nTesting root_cause_chain...")
    chain = queries.root_cause_chain("alert_1")
    print(f"Root cause: {chain['root_cause']}")
    
    print("\nTesting unpaged_teams...")
    teams = queries.unpaged_teams("incident_1")
    print(f"Unpaged teams: {[t['name'] for t in teams]}")
