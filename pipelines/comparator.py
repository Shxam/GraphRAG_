"""
Pipeline Comparator for PostMortemIQ
Compares all 4 pipelines: LLM-Only, Basic RAG, GraphRAG, Baseline LLM
Token reduction metric is GraphRAG vs Basic RAG (the hackathon judging standard)
"""

from typing import Dict, Any, Optional


class Comparator:
    """Compares all 4 pipeline results with Basic RAG as the primary baseline"""
    
    @staticmethod
    def compare_four(llm_only_result: Dict[str, Any],
                    basic_rag_result: Dict[str, Any],
                    graphrag_result: Dict[str, Any],
                    baseline_result: Dict[str, Any],
                    ground_truth: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Compare all 4 pipeline results
        PRIMARY METRIC: GraphRAG vs Basic RAG (hackathon judging standard)
        
        Args:
            llm_only_result: Result from LLM-only pipeline (no retrieval)
            basic_rag_result: Result from Basic RAG pipeline (vector-only)
            graphrag_result: Result from GraphRAG pipeline (vector + graph)
            baseline_result: Result from Baseline LLM pipeline (full context dump)
            ground_truth: Optional ground truth for accuracy calculation
            
        Returns:
            Comparison metrics for all 4 pipelines
        """
        # Extract tokens
        llm_only_tokens = llm_only_result["total_tokens"]
        basic_rag_tokens = basic_rag_result["total_tokens"]
        graphrag_tokens = graphrag_result["total_tokens"]
        baseline_tokens = baseline_result["total_tokens"]
        
        # PRIMARY METRIC: GraphRAG vs Basic RAG (what judges score)
        token_reduction_vs_basic_rag = ((basic_rag_tokens - graphrag_tokens) / basic_rag_tokens) * 100 if basic_rag_tokens > 0 else 0.0
        
        # Secondary comparisons for context
        token_reduction_vs_baseline = ((baseline_tokens - graphrag_tokens) / baseline_tokens) * 100 if baseline_tokens > 0 else 0.0
        
        # Extract latencies
        llm_only_latency = llm_only_result["latency_ms"]
        basic_rag_latency = basic_rag_result["latency_ms"]
        graphrag_latency = graphrag_result["latency_ms"]
        baseline_latency = baseline_result["latency_ms"]
        
        # PRIMARY METRIC: GraphRAG vs Basic RAG
        latency_reduction_vs_basic_rag = ((basic_rag_latency - graphrag_latency) / basic_rag_latency) * 100 if basic_rag_latency > 0 else 0.0
        latency_reduction_vs_baseline = ((baseline_latency - graphrag_latency) / baseline_latency) * 100 if baseline_latency > 0 else 0.0
        
        # Extract costs
        llm_only_cost = llm_only_result["cost_usd"]
        basic_rag_cost = basic_rag_result["cost_usd"]
        graphrag_cost = graphrag_result["cost_usd"]
        baseline_cost = baseline_result["cost_usd"]
        
        # PRIMARY METRIC: GraphRAG vs Basic RAG
        cost_savings_vs_basic_rag = ((basic_rag_cost - graphrag_cost) / basic_rag_cost) * 100 if basic_rag_cost > 0 else 0.0
        cost_savings_vs_baseline = ((baseline_cost - graphrag_cost) / baseline_cost) * 100 if baseline_cost > 0 else 0.0
        
        # Accuracy comparison (if ground truth provided)
        accuracy_llm_only = None
        accuracy_basic_rag = None
        accuracy_graphrag = None
        accuracy_baseline = None
        
        if ground_truth:
            accuracy_llm_only = Comparator._check_accuracy(
                llm_only_result["rca_report"],
                ground_truth
            )
            accuracy_basic_rag = Comparator._check_accuracy(
                basic_rag_result["rca_report"],
                ground_truth
            )
            accuracy_graphrag = Comparator._check_accuracy(
                graphrag_result["rca_report"],
                ground_truth
            )
            accuracy_baseline = Comparator._check_accuracy(
                baseline_result["rca_report"],
                ground_truth
            )
        
        return {
            "incident_id": graphrag_result["incident_id"],
            
            # PRIMARY HEADLINE METRICS (GraphRAG vs Basic RAG)
            "token_reduction_pct": token_reduction_vs_basic_rag,
            "cost_savings_pct": cost_savings_vs_basic_rag,
            "latency_reduction_pct": latency_reduction_vs_basic_rag,
            
            # Token metrics (all 4 pipelines)
            "llm_only_tokens": llm_only_tokens,
            "basic_rag_tokens": basic_rag_tokens,
            "graphrag_tokens": graphrag_tokens,
            "baseline_tokens": baseline_tokens,
            
            # Secondary comparison (GraphRAG vs Baseline LLM)
            "token_reduction_vs_baseline_pct": token_reduction_vs_baseline,
            "cost_savings_vs_baseline_pct": cost_savings_vs_baseline,
            "latency_reduction_vs_baseline_pct": latency_reduction_vs_baseline,
            
            # Latency metrics (all 4 pipelines)
            "llm_only_latency_ms": llm_only_latency,
            "basic_rag_latency_ms": basic_rag_latency,
            "graphrag_latency_ms": graphrag_latency,
            "baseline_latency_ms": baseline_latency,
            
            # Cost metrics (all 4 pipelines)
            "llm_only_cost_usd": llm_only_cost,
            "basic_rag_cost_usd": basic_rag_cost,
            "graphrag_cost_usd": graphrag_cost,
            "baseline_cost_usd": baseline_cost,
            
            # Accuracy metrics (all 4 pipelines)
            "accuracy_llm_only": accuracy_llm_only,
            "accuracy_basic_rag": accuracy_basic_rag,
            "accuracy_graphrag": accuracy_graphrag,
            "accuracy_baseline": accuracy_baseline,
            
            # Hallucination metrics (all 4 pipelines)
            "hallucination_rate_llm_only": llm_only_result.get("hallucination_rate", 0),
            "hallucination_rate_basic_rag": basic_rag_result.get("hallucination_rate", 0),
            "hallucination_rate_graphrag": graphrag_result.get("hallucination_rate", 0),
            "hallucination_rate_baseline": baseline_result.get("hallucination_rate", 0),
            
            # Full results
            "llm_only_result": llm_only_result,
            "basic_rag_result": basic_rag_result,
            "graphrag_result": graphrag_result,
            "baseline_result": baseline_result
        }
    
    @staticmethod
    def compare_three(baseline_result: Dict[str, Any], 
                     graphrag_result: Dict[str, Any],
                     llm_only_result: Dict[str, Any],
                     ground_truth: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Compare three pipeline results
        
        Args:
            baseline_result: Result from baseline pipeline
            graphrag_result: Result from GraphRAG pipeline
            llm_only_result: Result from LLM-only pipeline
            ground_truth: Optional ground truth for accuracy calculation
            
        Returns:
            Comparison metrics for all three pipelines
        """
        # Token comparison
        baseline_tokens = baseline_result["total_tokens"]
        graphrag_tokens = graphrag_result["total_tokens"]
        llm_only_tokens = llm_only_result["total_tokens"]
        
        graphrag_vs_baseline_reduction = ((baseline_tokens - graphrag_tokens) / baseline_tokens) * 100 if baseline_tokens > 0 else 0.0
        llm_only_vs_baseline_reduction = ((baseline_tokens - llm_only_tokens) / baseline_tokens) * 100 if baseline_tokens > 0 else 0.0
        
        # Latency comparison
        baseline_latency = baseline_result["latency_ms"]
        graphrag_latency = graphrag_result["latency_ms"]
        llm_only_latency = llm_only_result["latency_ms"]
        
        graphrag_vs_baseline_latency = ((baseline_latency - graphrag_latency) / baseline_latency) * 100 if baseline_latency > 0 else 0.0
        llm_only_vs_baseline_latency = ((baseline_latency - llm_only_latency) / baseline_latency) * 100 if baseline_latency > 0 else 0.0
        
        # Cost comparison
        baseline_cost = baseline_result["cost_usd"]
        graphrag_cost = graphrag_result["cost_usd"]
        llm_only_cost = llm_only_result["cost_usd"]
        
        graphrag_vs_baseline_cost = ((baseline_cost - graphrag_cost) / baseline_cost) * 100 if baseline_cost > 0 else 0.0
        llm_only_vs_baseline_cost = ((baseline_cost - llm_only_cost) / baseline_cost) * 100 if baseline_cost > 0 else 0.0
        
        # Accuracy comparison (if ground truth provided)
        accuracy_baseline = None
        accuracy_graphrag = None
        accuracy_llm_only = None
        if ground_truth:
            accuracy_baseline = Comparator._check_accuracy(
                baseline_result["rca_report"],
                ground_truth
            )
            accuracy_graphrag = Comparator._check_accuracy(
                graphrag_result["rca_report"],
                ground_truth
            )
            accuracy_llm_only = Comparator._check_accuracy(
                llm_only_result["rca_report"],
                ground_truth
            )
        
        return {
            "incident_id": baseline_result["incident_id"],
            
            # Token metrics
            "baseline_tokens": baseline_tokens,
            "graphrag_tokens": graphrag_tokens,
            "llm_only_tokens": llm_only_tokens,
            "graphrag_token_reduction_pct": graphrag_vs_baseline_reduction,
            "llm_only_token_reduction_pct": llm_only_vs_baseline_reduction,
            
            # Latency metrics
            "baseline_latency_ms": baseline_latency,
            "graphrag_latency_ms": graphrag_latency,
            "llm_only_latency_ms": llm_only_latency,
            "graphrag_latency_reduction_pct": graphrag_vs_baseline_latency,
            "llm_only_latency_reduction_pct": llm_only_vs_baseline_latency,
            
            # Cost metrics
            "baseline_cost_usd": baseline_cost,
            "graphrag_cost_usd": graphrag_cost,
            "llm_only_cost_usd": llm_only_cost,
            "graphrag_cost_savings_pct": graphrag_vs_baseline_cost,
            "llm_only_cost_savings_pct": llm_only_vs_baseline_cost,
            
            # Accuracy metrics
            "accuracy_baseline": accuracy_baseline,
            "accuracy_graphrag": accuracy_graphrag,
            "accuracy_llm_only": accuracy_llm_only,
            
            # Hallucination metrics
            "hallucination_rate_baseline": baseline_result.get("hallucination_rate", 0),
            "hallucination_rate_graphrag": graphrag_result.get("hallucination_rate", 0),
            "hallucination_rate_llm_only": llm_only_result.get("hallucination_rate", 0),
            
            # Full results
            "baseline_result": baseline_result,
            "graphrag_result": graphrag_result,
            "llm_only_result": llm_only_result
        }
    
    @staticmethod
    def compare(baseline_result: Dict[str, Any], 
                graphrag_result: Dict[str, Any],
                ground_truth: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Compare two pipeline results (backward compatibility)
        
        Args:
            baseline_result: Result from baseline pipeline
            graphrag_result: Result from GraphRAG pipeline
            ground_truth: Optional ground truth for accuracy calculation
            
        Returns:
            Comparison metrics
        """
        # Token comparison
        token_delta = baseline_result["total_tokens"] - graphrag_result["total_tokens"]
        token_reduction_pct = (token_delta / baseline_result["total_tokens"]) * 100 if baseline_result["total_tokens"] > 0 else 0.0
        
        # Latency comparison
        latency_delta = baseline_result["latency_ms"] - graphrag_result["latency_ms"]
        latency_reduction_pct = (latency_delta / baseline_result["latency_ms"]) * 100 if baseline_result["latency_ms"] > 0 else 0.0
        
        # Cost comparison
        cost_delta = baseline_result["cost_usd"] - graphrag_result["cost_usd"]
        cost_savings_pct = (cost_delta / baseline_result["cost_usd"]) * 100 if baseline_result["cost_usd"] > 0 else 0.0
        
        # Accuracy comparison (if ground truth provided)
        accuracy_baseline = None
        accuracy_graphrag = None
        if ground_truth:
            accuracy_baseline = Comparator._check_accuracy(
                baseline_result["rca_report"],
                ground_truth
            )
            accuracy_graphrag = Comparator._check_accuracy(
                graphrag_result["rca_report"],
                ground_truth
            )
        
        # Hallucination comparison
        hallucination_delta = (
            graphrag_result.get("hallucination_rate", 0) - 
            baseline_result.get("hallucination_rate", 0)
        )
        
        return {
            "incident_id": baseline_result["incident_id"],
            
            # Token metrics
            "baseline_tokens": baseline_result["total_tokens"],
            "graphrag_tokens": graphrag_result["total_tokens"],
            "token_delta": token_delta,
            "token_reduction_pct": token_reduction_pct,
            
            # Latency metrics
            "baseline_latency_ms": baseline_result["latency_ms"],
            "graphrag_latency_ms": graphrag_result["latency_ms"],
            "latency_delta_ms": latency_delta,
            "latency_reduction_pct": latency_reduction_pct,
            
            # Cost metrics
            "baseline_cost_usd": baseline_result["cost_usd"],
            "graphrag_cost_usd": graphrag_result["cost_usd"],
            "cost_delta_usd": cost_delta,
            "cost_savings_pct": cost_savings_pct,
            
            # Accuracy metrics
            "accuracy_baseline": accuracy_baseline,
            "accuracy_graphrag": accuracy_graphrag,
            
            # Hallucination metrics
            "hallucination_rate_baseline": baseline_result.get("hallucination_rate", 0),
            "hallucination_rate_graphrag": graphrag_result.get("hallucination_rate", 0),
            "hallucination_delta": hallucination_delta,
            
            # Full results
            "baseline_result": baseline_result,
            "graphrag_result": graphrag_result
        }
    
    @staticmethod
    def _check_accuracy(rca_report: str, ground_truth: Dict[str, Any]) -> bool:
        """
        Check if RCA report correctly identifies ground truth root cause
        
        Args:
            rca_report: The LLM's RCA report
            ground_truth: Ground truth data
            
        Returns:
            True if root cause correctly identified
        """
        root_cause_id = ground_truth.get("ground_truth_root_cause", "")
        
        # Simple check: does the report mention the root cause ID?
        # In production, this would be more sophisticated
        return root_cause_id.lower() in rca_report.lower()
    
    @staticmethod
    def aggregate_results(comparisons: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate multiple comparison results for benchmark
        
        Args:
            comparisons: List of comparison results
            
        Returns:
            Aggregated metrics
        """
        if not comparisons:
            return {}
        
        n = len(comparisons)
        
        # Check if we have 4-way comparisons (with Basic RAG)
        has_basic_rag = "basic_rag_tokens" in comparisons[0]
        has_llm_only = "llm_only_tokens" in comparisons[0]
        
        result = {
            "total_incidents": n,
            
            # PRIMARY METRICS (GraphRAG vs Basic RAG - what judges score)
            "avg_token_reduction_pct": sum(c.get("token_reduction_pct", 0) for c in comparisons) / n,
            "avg_cost_savings_pct": sum(c.get("cost_savings_pct", 0) for c in comparisons) / n,
            "avg_latency_reduction_pct": sum(c.get("latency_reduction_pct", 0) for c in comparisons) / n,
            
            # Accuracy rates
            "graphrag_accuracy_rate": sum(1 for c in comparisons if c.get("accuracy_graphrag")) / n if any(c.get("accuracy_graphrag") is not None for c in comparisons) else None,
        }
        
        if has_basic_rag:
            result.update({
                # Average tokens per pipeline
                "avg_llm_only_tokens": sum(c.get("llm_only_tokens", 0) for c in comparisons) / n,
                "avg_basic_rag_tokens": sum(c.get("basic_rag_tokens", 0) for c in comparisons) / n,
                "avg_graphrag_tokens": sum(c.get("graphrag_tokens", 0) for c in comparisons) / n,
                "avg_baseline_tokens": sum(c.get("baseline_tokens", 0) for c in comparisons) / n,
                
                # Average latencies
                "avg_llm_only_latency_ms": sum(c.get("llm_only_latency_ms", 0) for c in comparisons) / n,
                "avg_basic_rag_latency_ms": sum(c.get("basic_rag_latency_ms", 0) for c in comparisons) / n,
                "avg_graphrag_latency_ms": sum(c.get("graphrag_latency_ms", 0) for c in comparisons) / n,
                "avg_baseline_latency_ms": sum(c.get("baseline_latency_ms", 0) for c in comparisons) / n,
                
                # Average costs
                "avg_llm_only_cost_usd": sum(c.get("llm_only_cost_usd", 0) for c in comparisons) / n,
                "avg_basic_rag_cost_usd": sum(c.get("basic_rag_cost_usd", 0) for c in comparisons) / n,
                "avg_graphrag_cost_usd": sum(c.get("graphrag_cost_usd", 0) for c in comparisons) / n,
                "avg_baseline_cost_usd": sum(c.get("baseline_cost_usd", 0) for c in comparisons) / n,
                
                # Accuracy rates for all pipelines
                "llm_only_accuracy_rate": sum(1 for c in comparisons if c.get("accuracy_llm_only")) / n if any(c.get("accuracy_llm_only") is not None for c in comparisons) else None,
                "basic_rag_accuracy_rate": sum(1 for c in comparisons if c.get("accuracy_basic_rag")) / n if any(c.get("accuracy_basic_rag") is not None for c in comparisons) else None,
                "baseline_accuracy_rate": sum(1 for c in comparisons if c.get("accuracy_baseline")) / n if any(c.get("accuracy_baseline") is not None for c in comparisons) else None,
                
                # Hallucination rates
                "avg_hallucination_rate_llm_only": sum(c.get("hallucination_rate_llm_only", 0) for c in comparisons) / n,
                "avg_hallucination_rate_basic_rag": sum(c.get("hallucination_rate_basic_rag", 0) for c in comparisons) / n,
                "avg_hallucination_rate_graphrag": sum(c.get("hallucination_rate_graphrag", 0) for c in comparisons) / n,
                "avg_hallucination_rate_baseline": sum(c.get("hallucination_rate_baseline", 0) for c in comparisons) / n,
                
                # Secondary metrics (GraphRAG vs Baseline LLM)
                "avg_token_reduction_vs_baseline_pct": sum(c.get("token_reduction_vs_baseline_pct", 0) for c in comparisons) / n,
                "avg_cost_savings_vs_baseline_pct": sum(c.get("cost_savings_vs_baseline_pct", 0) for c in comparisons) / n,
                "avg_latency_reduction_vs_baseline_pct": sum(c.get("latency_reduction_vs_baseline_pct", 0) for c in comparisons) / n,
            })
        elif has_llm_only:
            # Legacy 3-way comparison support
            result.update({
                "avg_graphrag_token_reduction_pct": sum(c.get("graphrag_token_reduction_pct", c.get("token_reduction_pct", 0)) for c in comparisons) / n,
                "avg_graphrag_cost_savings_pct": sum(c.get("graphrag_cost_savings_pct", c.get("cost_savings_pct", 0)) for c in comparisons) / n,
                "avg_graphrag_latency_reduction_pct": sum(c.get("graphrag_latency_reduction_pct", c.get("latency_reduction_pct", 0)) for c in comparisons) / n,
                "total_cost_saved_usd": sum(c.get("baseline_cost_usd", 0) - c.get("graphrag_cost_usd", 0) for c in comparisons),
                "baseline_accuracy_rate": sum(1 for c in comparisons if c.get("accuracy_baseline")) / n if any(c.get("accuracy_baseline") is not None for c in comparisons) else None,
                "avg_hallucination_rate_baseline": sum(c.get("hallucination_rate_baseline", 0) for c in comparisons) / n,
                "avg_hallucination_rate_graphrag": sum(c.get("hallucination_rate_graphrag", 0) for c in comparisons) / n,
                "avg_llm_only_token_reduction_pct": sum(c.get("llm_only_token_reduction_pct", 0) for c in comparisons) / n,
                "avg_llm_only_cost_savings_pct": sum(c.get("llm_only_cost_savings_pct", 0) for c in comparisons) / n,
                "avg_llm_only_latency_reduction_pct": sum(c.get("llm_only_latency_reduction_pct", 0) for c in comparisons) / n,
                "llm_only_accuracy_rate": sum(1 for c in comparisons if c.get("accuracy_llm_only")) / n if any(c.get("accuracy_llm_only") is not None for c in comparisons) else None,
                "avg_hallucination_rate_llm_only": sum(c.get("hallucination_rate_llm_only", 0) for c in comparisons) / n
            })
        
        return result


if __name__ == "__main__":
    # Test comparison
    baseline = {
        "incident_id": "incident_1",
        "total_tokens": 11500,
        "latency_ms": 4200,
        "cost_usd": 0.0092,
        "rca_report": "The issue appears to be related to auth-svc...",
        "hallucination_rate": 0.23
    }
    
    graphrag = {
        "incident_id": "incident_1",
        "total_tokens": 380,
        "latency_ms": 890,
        "cost_usd": 0.0003,
        "rca_report": "Root cause: config_3 JWT_EXPIRY_SECONDS changed from 3600 to 60",
        "hallucination_rate": 0.02
    }
    
    ground_truth = {
        "ground_truth_root_cause": "config_3"
    }
    
    comparison = Comparator.compare(baseline, graphrag, ground_truth)
    print(f"Comparison Result:")
    print(f"  Token reduction: {comparison['token_reduction_pct']:.1f}%")
    print(f"  Cost savings: {comparison['cost_savings_pct']:.1f}%")
    print(f"  Latency reduction: {comparison['latency_reduction_pct']:.1f}%")
    print(f"  GraphRAG accuracy: {comparison['accuracy_graphrag']}")
    print(f"  Baseline accuracy: {comparison['accuracy_baseline']}")
