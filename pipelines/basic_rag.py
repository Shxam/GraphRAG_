"""
Basic RAG Pipeline for PostMortemIQ
Vector-only retrieval using sentence-transformers + FAISS
This is the baseline that GraphRAG is compared against for token reduction metrics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import pickle
from typing import Dict, Any, List
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Run: pip install sentence-transformers faiss-cpu")

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("Warning: tiktoken not installed. Run: pip install tiktoken")

from llm.groq_client import GroqClient
from llm.prompt_builder import PromptBuilder


class BasicRAGPipeline:
    """
    Basic RAG pipeline using vector similarity search only.
    This represents the standard RAG approach without graph traversal.
    """
    
    def __init__(self):
        self.groq_client = GroqClient()
        self.prompt_builder = PromptBuilder()
        self.model = None
        self.index = None
        self.chunks = []
        self.cache_dir = "data/.rag_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize on first use
        self._initialized = False
    
    def _initialize(self):
        """Initialize the RAG system (lazy loading)"""
        if self._initialized:
            return
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers required. Run: pip install sentence-transformers faiss-cpu")
        
        print("Initializing Basic RAG pipeline...")
        
        # Load or create FAISS index
        index_path = "data/faiss.index"
        chunks_path = "data/chunks.pkl"
        
        if os.path.exists(index_path) and os.path.exists(chunks_path):
            print("Loading cached FAISS index from data/faiss.index...")
            self.index = faiss.read_index(index_path)
            with open(chunks_path, 'rb') as f:
                self.chunks = pickle.load(f)
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            print(f"Loaded {len(self.chunks)} chunks from cache")
        else:
            raise FileNotFoundError("FAISS index not found! Run python scripts/ingest_postmortems.py first.")
        
        self._initialized = True
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve top-k most similar chunks using vector similarity
        
        Args:
            query: Query string
            top_k: Number of chunks to retrieve
            
        Returns:
            List of retrieved chunks with similarity scores
        """
        if not self._initialized:
            self._initialize()
        
        # Encode query
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.chunks):
                # Our chunks are just strings, so format them into dicts expected by run()
                text = self.chunks[idx]
                results.append({
                    'text': text,
                    'similarity_score': float(score)
                })
        
        return results
    
    def run(self, incident_id: str, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Basic RAG pipeline on an incident
        
        Args:
            incident_id: The incident identifier
            incident_data: Incident information
            
        Returns:
            Pipeline result with RCA, tokens, latency, cost
        """
        start_time = time.time()
        
        try:
            # Build query from incident data
            query = f"{incident_data.get('alert_name', 'Unknown alert')} {incident_data.get('severity', '')} incident"
            
            # Retrieve similar chunks
            retrieved_chunks = self.retrieve(query, top_k=5)
            
            # Build context from retrieved chunks
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks, 1):
                context_parts.append(
                    f"[Chunk {i}] (similarity: {chunk['similarity_score']:.3f})\n"
                    f"{chunk['text']}\n"
                )
            
            context = "\n".join(context_parts)
            
            # Build prompt
            prompt = self.prompt_builder.build_rag_prompt(context, incident_id, incident_data)
            
            # Call LLM
            llm_result = self.groq_client.call_llm(prompt)
            
            # Count tokens
            if TIKTOKEN_AVAILABLE:
                enc = tiktoken.get_encoding("cl100k_base")
                actual_input_tokens = len(enc.encode(prompt))
            else:
                actual_input_tokens = llm_result["input_tokens"]
            
            # Calculate cost
            cost = self.groq_client.calculate_cost(
                llm_result["input_tokens"],
                llm_result["output_tokens"]
            )
            
            total_latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "pipeline": "basic_rag",
                "incident_id": incident_id,
                "rca_report": llm_result["response"],
                "input_tokens": llm_result["input_tokens"],
                "output_tokens": llm_result["output_tokens"],
                "total_tokens": llm_result["total_tokens"],
                "latency_ms": total_latency_ms,
                "llm_latency_ms": llm_result["latency_ms"],
                "retrieval_latency_ms": total_latency_ms - llm_result["latency_ms"],
                "cost_usd": cost,
                "retrieved_chunks": len(retrieved_chunks),
                "context_size": len(context),
                "model": "llama-3.3-70b-versatile"
            }
            
        except Exception as e:
            # Graceful error handling
            return {
                "pipeline": "basic_rag",
                "incident_id": incident_id,
                "rca_report": f"Error in Basic RAG pipeline: {str(e)}",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_ms": int((time.time() - start_time) * 1000),
                "llm_latency_ms": 0,
                "retrieval_latency_ms": 0,
                "cost_usd": 0.0,
                "retrieved_chunks": 0,
                "context_size": 0,
                "error": str(e),
                "model": "llama-3.3-70b-versatile"
            }


if __name__ == "__main__":
    # Test the pipeline
    pipeline = BasicRAGPipeline()
    
    test_incident = {
        "incident_id": "incident_1",
        "alert_id": "alert_1",
        "alert_name": "High error rate in auth-svc",
        "severity": "critical",
        "start_time": "2024-01-15T14:33:00Z"
    }
    
    print("Testing Basic RAG Pipeline...")
    result = pipeline.run("incident_1", test_incident)
    
    print(f"\nBasic RAG Pipeline Result:")
    print(f"  Tokens: {result['total_tokens']}")
    print(f"  Latency: {result['latency_ms']}ms")
    print(f"  Cost: ${result['cost_usd']:.6f}")
    print(f"  Retrieved chunks: {result['retrieved_chunks']}")
    print(f"  Context size: {result['context_size']} chars")
