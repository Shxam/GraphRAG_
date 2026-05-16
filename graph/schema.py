"""
TigerGraph Schema Definition for PostMortemIQ
Defines vertex and edge types for the incident causal graph
"""

import pyTigerGraph as tg
import os
from dotenv import load_dotenv

load_dotenv()


class GraphSchema:
    """Manages TigerGraph schema for incident analysis"""
    
    def __init__(self):
        self.conn = None
        try:
            self.conn = tg.TigerGraphConnection(
                host=os.getenv("TIGERGRAPH_HOST"),
                username=os.getenv("TIGERGRAPH_USERNAME"),
                password=os.getenv("TIGERGRAPH_PASSWORD"),
                graphname=os.getenv("TIGERGRAPH_GRAPH_NAME", "IncidentGraph")
            )
        except Exception:
            pass
    
    def create_schema(self):
        """Create all vertex and edge types"""
        
        # Vertex definitions
        vertices = {
            "Alert": ["alert_id STRING PRIMARY KEY", "name STRING", "severity STRING", 
                     "timestamp DATETIME", "status STRING"],
            "Service": ["service_id STRING PRIMARY KEY", "name STRING", "team_owner STRING",
                       "sla_tier STRING", "language STRING", "repo_url STRING"],
            "Deployment": ["deploy_id STRING PRIMARY KEY", "version STRING", "timestamp DATETIME",
                          "deployer STRING", "diff_summary STRING"],
            "ConfigChange": ["change_id STRING PRIMARY KEY", "key STRING", "old_value STRING",
                           "new_value STRING", "timestamp DATETIME", "changer STRING"],
            "Dependency": ["dep_id STRING PRIMARY KEY", "name STRING", "version_pinned STRING",
                          "type STRING"],
            "Team": ["team_id STRING PRIMARY KEY", "name STRING", "on_call_engineer STRING",
                    "escalation_path STRING", "pagerduty_id STRING"],
            "Runbook": ["runbook_id STRING PRIMARY KEY", "title STRING", "steps_summary STRING",
                       "last_used DATETIME", "url STRING"],
            # Phase 1: Added mttr_minutes and resolution_summary to Incident vertex
            "Incident": ["incident_id STRING PRIMARY KEY", "severity STRING", "start_time DATETIME",
                        "end_time DATETIME", "status STRING",
                        "mttr_minutes FLOAT", "resolution_summary STRING"]
        }
        
        # Edge definitions
        edges = {
            "fired_on": ("Alert", "Service", ["timestamp DATETIME"]),
            "had_deployment": ("Service", "Deployment", ["at_timestamp DATETIME"]),
            "changed_config": ("Deployment", "ConfigChange", []),
            "broke_dependency": ("ConfigChange", "Dependency", ["confidence_score FLOAT"]),
            "used_by": ("Dependency", "Service", []),
            "owned_by": ("Service", "Team", []),
            "has_runbook": ("Service", "Runbook", ["issue_type STRING"]),
            "calls": ("Service", "Service", ["protocol STRING", "timeout_ms INT"]),
            "part_of": ("Alert", "Incident", []),
            # Phase 1: New edges
            "directly_affects": ("ConfigChange", "Service", ["confidence_score FLOAT"]),
            "similar_to": ("Incident", "Incident", ["similarity_score FLOAT"]),
        }
        
        print("Schema definition ready. Deploy manually in TigerGraph Studio.")
        return vertices, edges
    
    def verify_schema(self):
        """Verify schema is correctly loaded"""
        try:
            schema = self.conn.getSchema()
            print(f"✓ Schema verified: {len(schema['VertexTypes'])} vertex types, {len(schema['EdgeTypes'])} edge types")
            return True
        except Exception as e:
            print(f"✗ Schema verification failed: {e}")
            return False


if __name__ == "__main__":
    schema = GraphSchema()
    vertices, edges = schema.create_schema()
    print("\nVertex Types:", list(vertices.keys()))
    print("Edge Types:", list(edges.keys()))
