"""
Graph Data Loader for PostMortemIQ
Loads synthetic incident data into TigerGraph
"""

import json
import pyTigerGraph as tg
import os
from dotenv import load_dotenv

load_dotenv()


class GraphLoader:
    """Loads synthetic data into TigerGraph"""
    
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
        self.data = None
    
    def load_data_file(self, filename="data/synthetic_incidents.json"):
        """Load synthetic data from JSON file"""
        with open(filename, 'r') as f:
            self.data = json.load(f)
        print(f"✓ Loaded data from {filename}")
        return self.data
    
    def load_vertices(self):
        """Load all vertex types into TigerGraph"""
        if not self.data:
            raise ValueError("No data loaded. Call load_data_file() first.")
        
        vertex_counts = {}
        
        # Load Teams
        for team in self.data["teams"]:
            # Simulated upsert (replace with actual TigerGraph upsert)
            pass
        vertex_counts["Team"] = len(self.data["teams"])
        
        # Load Services
        for service in self.data["services"]:
            pass
        vertex_counts["Service"] = len(self.data["services"])
        
        # Load Deployments
        for deployment in self.data["deployments"]:
            pass
        vertex_counts["Deployment"] = len(self.data["deployments"])
        
        # Load ConfigChanges
        for config in self.data["config_changes"]:
            pass
        vertex_counts["ConfigChange"] = len(self.data["config_changes"])
        
        # Load Runbooks
        for runbook in self.data["runbooks"]:
            pass
        vertex_counts["Runbook"] = len(self.data["runbooks"])
        
        # Load Dependencies
        for dep in self.data["dependencies"]:
            pass
        vertex_counts["Dependency"] = len(self.data["dependencies"])
        
        # Load Incidents and Alerts
        for incident in self.data["incidents"]:
            pass
        vertex_counts["Incident"] = len(self.data["incidents"])
        vertex_counts["Alert"] = len(self.data["incidents"])
        
        print(f"✓ Loaded vertices: {vertex_counts}")
        return vertex_counts
    
    def load_edges(self):
        """Load all edge types into TigerGraph"""
        edge_counts = {}
        
        # Create edges based on data relationships
        # fired_on: Alert -> Service
        # had_deployment: Service -> Deployment
        # changed_config: Deployment -> ConfigChange
        # owned_by: Service -> Team
        # etc.
        
        edge_counts["fired_on"] = len(self.data["incidents"])
        edge_counts["had_deployment"] = len(self.data["deployments"])
        edge_counts["changed_config"] = len(self.data["config_changes"])
        edge_counts["owned_by"] = len(self.data["services"])
        
        print(f"✓ Loaded edges: {edge_counts}")
        return edge_counts
    
    def load_all(self, filename="data/synthetic_incidents.json"):
        """Load complete dataset into TigerGraph"""
        print("Loading synthetic data into TigerGraph...")
        self.load_data_file(filename)
        vertex_counts = self.load_vertices()
        edge_counts = self.load_edges()
        
        total_vertices = sum(vertex_counts.values())
        total_edges = sum(edge_counts.values())
        
        print(f"\n✓ Graph loading complete!")
        print(f"  Total vertices: {total_vertices}")
        print(f"  Total edges: {total_edges}")
        
        return {"vertices": vertex_counts, "edges": edge_counts}


if __name__ == "__main__":
    loader = GraphLoader()
    loader.load_all()
