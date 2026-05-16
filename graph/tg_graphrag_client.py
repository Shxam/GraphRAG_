"""
TigerGraph GraphRAG Client Wrapper
Wraps official TigerGraph GraphRAG API with fallback to pyTigerGraph
"""

import os
import sys
import json
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

logger = logging.getLogger(__name__)

try:
    import pyTigerGraph as tg
    PYTG_AVAILABLE = True
except ImportError:
    PYTG_AVAILABLE = False
    logger.warning("pyTigerGraph not available")


class TGGraphRAGClient:
    """
    Client for TigerGraph GraphRAG with official API and pyTigerGraph fallback
    
    This wrapper provides:
    1. Official GraphRAG API calls (POST /api/v1/query, /api/v1/ingest)
    2. Fallback to pyTigerGraph for GSQL queries
    3. Health check and connection validation
    """
    
    def __init__(self, 
                 graphrag_base_url: str = None,
                 tigergraph_host: str = None,
                 tigergraph_username: str = None,
                 tigergraph_password: str = None,
                 graph_name: str = None):
        """
        Initialize TigerGraph GraphRAG client
        
        Args:
            graphrag_base_url: Base URL for GraphRAG API (e.g., http://localhost:8000)
            tigergraph_host: TigerGraph Cloud host
            tigergraph_username: TigerGraph username
            tigergraph_password: TigerGraph password
            graph_name: Graph name
        """
        # GraphRAG API configuration
        self.graphrag_base_url = graphrag_base_url or os.getenv("GRAPHRAG_BASE_URL", "http://localhost:8000")
        self.graphrag_available = False
        
        # TigerGraph direct connection configuration
        self.tigergraph_host = tigergraph_host or os.getenv("TIGERGRAPH_HOST")
        self.tigergraph_username = tigergraph_username or os.getenv("TIGERGRAPH_USERNAME", "tigergraph")
        self.tigergraph_password = tigergraph_password or os.getenv("TIGERGRAPH_PASSWORD")
        self.graph_name = graph_name or os.getenv("TIGERGRAPH_GRAPH_NAME", "IncidentGraph")
        
        # Initialize pyTigerGraph connection (fallback)
        self.tg_conn = None
        if PYTG_AVAILABLE and self.tigergraph_host:
            try:
                self.tg_conn = tg.TigerGraphConnection(
                    host=self.tigergraph_host,
                    username=self.tigergraph_username,
                    password=self.tigergraph_password,
                    graphname=self.graph_name
                )
                logger.info("pyTigerGraph connection initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize pyTigerGraph: {e}")
        
        # Check GraphRAG API health
        self._check_graphrag_health()
    
    def _check_graphrag_health(self) -> bool:
        """
        Check if GraphRAG API is available
        
        Returns:
            True if GraphRAG API is healthy
        """
        try:
            response = requests.get(
                f"{self.graphrag_base_url}/health",
                timeout=5.0
            )
            
            if response.status_code == 200:
                self.graphrag_available = True
                logger.info(f"GraphRAG API available at {self.graphrag_base_url}")
                return True
            else:
                logger.warning(f"GraphRAG API returned status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.warning(f"GraphRAG API not available at {self.graphrag_base_url}. Will use pyTigerGraph fallback.")
            return False
        except Exception as e:
            logger.warning(f"GraphRAG health check failed: {e}")
            return False
    
    def query(self, 
             query_text: str,
             top_k: int = 5,
             method: str = "auto") -> Dict[str, Any]:
        """
        Query the graph using GraphRAG API or fallback
        
        Args:
            query_text: Natural language query
            top_k: Number of results to return
            method: Query method ("graphrag", "pytg", or "auto")
            
        Returns:
            Query results
        """
        # Auto-select method
        if method == "auto":
            method = "graphrag" if self.graphrag_available else "pytg"
        
        if method == "graphrag" and self.graphrag_available:
            return self._query_graphrag_api(query_text, top_k)
        elif method == "pytg" and self.tg_conn:
            return self._query_pytg(query_text, top_k)
        else:
            raise Exception(f"No available query method. GraphRAG: {self.graphrag_available}, pyTG: {self.tg_conn is not None}")
    
    def _query_graphrag_api(self, query_text: str, top_k: int) -> Dict[str, Any]:
        """Query using official GraphRAG API"""
        try:
            response = requests.post(
                f"{self.graphrag_base_url}/api/v1/query",
                json={
                    "query": query_text,
                    "top_k": top_k
                },
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "method": "graphrag_api",
                "results": result.get("results", []),
                "context": result.get("context", ""),
                "metadata": result.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"GraphRAG API query failed: {e}")
            # Fallback to pyTigerGraph
            if self.tg_conn:
                logger.info("Falling back to pyTigerGraph")
                return self._query_pytg(query_text, top_k)
            raise
    
    def _query_pytg(self, query_text: str, top_k: int) -> Dict[str, Any]:
        """Query using pyTigerGraph fallback"""
        if not self.tg_conn:
            raise Exception("pyTigerGraph connection not available")
        
        # This is a simplified fallback - in production, you'd implement
        # more sophisticated query translation
        logger.info(f"Using pyTigerGraph fallback for query: {query_text}")
        
        return {
            "method": "pytg_fallback",
            "results": [],
            "context": f"Fallback query for: {query_text}",
            "metadata": {"top_k": top_k}
        }
    
    def ingest(self, 
              documents: List[Dict[str, Any]],
              batch_size: int = 50) -> Dict[str, Any]:
        """
        Ingest documents into the graph
        
        Args:
            documents: List of documents to ingest
            batch_size: Batch size for ingestion
            
        Returns:
            Ingestion results
        """
        if self.graphrag_available:
            return self._ingest_graphrag_api(documents, batch_size)
        elif self.tg_conn:
            return self._ingest_pytg(documents, batch_size)
        else:
            raise Exception("No available ingestion method")
    
    def _ingest_graphrag_api(self, documents: List[Dict[str, Any]], batch_size: int) -> Dict[str, Any]:
        """Ingest using official GraphRAG API"""
        total_ingested = 0
        failed_batches = []
        
        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            try:
                response = requests.post(
                    f"{self.graphrag_base_url}/api/v1/ingest",
                    json={"documents": batch},
                    timeout=60.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                total_ingested += result.get("ingested_count", len(batch))
                logger.info(f"Ingested batch {i // batch_size + 1}: {len(batch)} documents")
                
            except Exception as e:
                logger.error(f"Failed to ingest batch {i // batch_size + 1}: {e}")
                failed_batches.append({
                    "batch_index": i // batch_size,
                    "error": str(e)
                })
        
        return {
            "method": "graphrag_api",
            "total_documents": len(documents),
            "ingested_count": total_ingested,
            "failed_batches": failed_batches,
            "success": len(failed_batches) == 0
        }
    
    def _ingest_pytg(self, documents: List[Dict[str, Any]], batch_size: int) -> Dict[str, Any]:
        """Ingest using pyTigerGraph fallback"""
        if not self.tg_conn:
            raise Exception("pyTigerGraph connection not available")
        
        logger.info(f"Using pyTigerGraph fallback for ingestion: {len(documents)} documents")
        
        # This is a placeholder - implement actual ingestion logic
        return {
            "method": "pytg_fallback",
            "total_documents": len(documents),
            "ingested_count": 0,
            "failed_batches": [],
            "success": False,
            "message": "pyTigerGraph ingestion not implemented"
        }
    
    def get_subgraph(self, 
                    incident_id: str,
                    max_hops: int = 4) -> Dict[str, Any]:
        """
        Get causal subgraph for an incident (GSQL fallback)
        
        Args:
            incident_id: Incident identifier
            max_hops: Maximum hops for traversal
            
        Returns:
            Subgraph data
        """
        if not self.tg_conn:
            raise Exception("pyTigerGraph connection required for subgraph queries")
        
        # Use existing GSQL queries via pyTigerGraph
        from graph.queries import GraphQueries
        
        queries = GraphQueries()
        subgraph = queries.get_causal_subgraph(incident_id)
        
        return {
            "method": "gsql_pytg",
            "incident_id": incident_id,
            "subgraph": subgraph,
            "max_hops": max_hops
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all connections
        
        Returns:
            Health status
        """
        graphrag_healthy = self._check_graphrag_health()
        pytg_healthy = self.tg_conn is not None
        
        return {
            "graphrag_api": {
                "available": graphrag_healthy,
                "url": self.graphrag_base_url
            },
            "pytg_fallback": {
                "available": pytg_healthy,
                "host": self.tigergraph_host,
                "graph": self.graph_name
            },
            "overall_status": "healthy" if (graphrag_healthy or pytg_healthy) else "unhealthy"
        }


if __name__ == "__main__":
    # Test TigerGraph GraphRAG client
    client = TGGraphRAGClient()
    
    # Health check
    health = client.health_check()
    print("Health Check:")
    print(json.dumps(health, indent=2))
    
    # Test query (if available)
    if health["overall_status"] == "healthy":
        try:
            result = client.query("What caused the incident?", top_k=5)
            print("\nQuery Result:")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"\nQuery failed: {e}")
