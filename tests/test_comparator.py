"""
Tests for comparator module
"""

import pytest
from pipelines.comparator import Comparator


class TestComparator:
    """Tests for Comparator class"""
    
    def test_comparator_initialization(self):
        """Test comparator can be initialized"""
        comparator = Comparator()
        assert comparator is not None
    
    def test_compare_two_pipelines(self):
        """Test comparing two pipeline results"""
        baseline_result = {
            "incident_id": "test_1",
            "total_tokens": 11500,
            "latency_ms": 4200,
            "cost_usd": 0.0092,
            "rca_report": "Baseline RCA report",
            "hallucination_rate": 0.23
        }
        
        graphrag_result = {
            "incident_id": "test_1",
            "total_tokens": 380,
            "latency_ms": 890,
            "cost_usd": 0.0003,
            "rca_report": "GraphRAG RCA report with config_3",
            "hallucination_rate": 0.02
        }
        
        ground_truth = {
            "ground_truth_root_cause": "config_3"
        }
        
        comparison = Comparator.compare(baseline_result, graphrag_result, ground_truth)
        
        # Check comparison keys
        assert "incident_id" in comparison
        assert "token_reduction_pct" in comparison
        assert "latency_reduction_pct" in comparison
        assert "cost_savings_pct" in comparison
        assert "accuracy_baseline" in comparison
        assert "accuracy_graphrag" in comparison
        
        # Check calculations
        assert comparison["token_reduction_pct"] > 90  # Should be ~96%
        assert comparison["latency_reduction_pct"] > 70  # Should be ~79%
        assert comparison["cost_savings_pct"] > 90  # Should be ~96%
        
        # Check accuracy
        assert comparison["accuracy_graphrag"] == True  # Contains config_3
        assert comparison["accuracy_baseline"] == False  # Doesn't contain config_3
    
    def test_compare_three_pipelines(self):
        """Test comparing three pipeline results"""
        baseline_result = {
            "incident_id": "test_1",
            "total_tokens": 11500,
            "latency_ms": 4200,
            "cost_usd": 0.0092,
            "rca_report": "Baseline RCA",
            "hallucination_rate": 0.23
        }
        
        graphrag_result = {
            "incident_id": "test_1",
            "total_tokens": 380,
            "latency_ms": 890,
            "cost_usd": 0.0003,
            "rca_report": "GraphRAG RCA",
            "hallucination_rate": 0.02
        }
        
        llm_only_result = {
            "incident_id": "test_1",
            "total_tokens": 300,
            "latency_ms": 800,
            "cost_usd": 0.00024,
            "rca_report": "LLM-only RCA",
            "hallucination_rate": 0.15
        }
        
        comparison = Comparator.compare_three(baseline_result, graphrag_result, llm_only_result)
        
        # Check three-way comparison keys
        assert "baseline_tokens" in comparison
        assert "graphrag_tokens" in comparison
        assert "llm_only_tokens" in comparison
        assert "graphrag_token_reduction_pct" in comparison
        assert "llm_only_token_reduction_pct" in comparison
        assert "graphrag_cost_savings_pct" in comparison
        assert "llm_only_cost_savings_pct" in comparison
        
        # Check calculations
        assert comparison["graphrag_token_reduction_pct"] > 90
        assert comparison["llm_only_token_reduction_pct"] > 95
        assert comparison["graphrag_cost_savings_pct"] > 90
        assert comparison["llm_only_cost_savings_pct"] > 95
    
    def test_token_reduction_calculation(self):
        """Test token reduction percentage is calculated correctly"""
        baseline = {"incident_id": "test", "total_tokens": 10000, "latency_ms": 1000, 
                   "cost_usd": 0.01, "rca_report": "test", "hallucination_rate": 0}
        graphrag = {"incident_id": "test", "total_tokens": 400, "latency_ms": 500, 
                   "cost_usd": 0.001, "rca_report": "test", "hallucination_rate": 0}
        
        comparison = Comparator.compare(baseline, graphrag)
        
        # 10000 - 400 = 9600 saved
        # 9600 / 10000 = 0.96 = 96%
        assert comparison["token_reduction_pct"] == 96.0
    
    def test_cost_savings_calculation(self):
        """Test cost savings percentage is calculated correctly"""
        baseline = {"incident_id": "test", "total_tokens": 10000, "latency_ms": 1000, 
                   "cost_usd": 0.01, "rca_report": "test", "hallucination_rate": 0}
        graphrag = {"incident_id": "test", "total_tokens": 400, "latency_ms": 500, 
                   "cost_usd": 0.001, "rca_report": "test", "hallucination_rate": 0}
        
        comparison = Comparator.compare(baseline, graphrag)
        
        # 0.01 - 0.001 = 0.009 saved
        # 0.009 / 0.01 = 0.9 = 90%
        assert abs(comparison["cost_savings_pct"] - 90.0) < 0.01  # Allow small floating point error
    
    def test_aggregate_results(self):
        """Test aggregating multiple comparison results"""
        comparisons = [
            {
                "token_reduction_pct": 96.0,
                "cost_savings_pct": 96.0,
                "latency_reduction_pct": 79.0,
                "cost_delta_usd": 0.0089,
                "accuracy_graphrag": True,
                "accuracy_baseline": False,
                "hallucination_rate_baseline": 0.23,
                "hallucination_rate_graphrag": 0.02,
                "baseline_cost_usd": 0.0092,
                "graphrag_cost_usd": 0.0003
            },
            {
                "token_reduction_pct": 95.0,
                "cost_savings_pct": 95.0,
                "latency_reduction_pct": 80.0,
                "cost_delta_usd": 0.0088,
                "accuracy_graphrag": True,
                "accuracy_baseline": True,
                "hallucination_rate_baseline": 0.20,
                "hallucination_rate_graphrag": 0.03,
                "baseline_cost_usd": 0.0090,
                "graphrag_cost_usd": 0.0002
            }
        ]
        
        aggregate = Comparator.aggregate_results(comparisons)
        
        assert "total_incidents" in aggregate
        assert aggregate["total_incidents"] == 2
        assert "avg_token_reduction_pct" in aggregate
        assert aggregate["avg_token_reduction_pct"] == 95.5  # (96 + 95) / 2
        assert "avg_cost_savings_pct" in aggregate
        assert aggregate["avg_cost_savings_pct"] == 95.5
        assert "graphrag_accuracy_rate" in aggregate
        assert aggregate["graphrag_accuracy_rate"] == 1.0  # 2/2 = 100%
    
    def test_aggregate_results_with_llm_only(self):
        """Test aggregating results with LLM-only pipeline"""
        comparisons = [
            {
                "graphrag_token_reduction_pct": 96.0,
                "llm_only_token_reduction_pct": 97.0,
                "graphrag_cost_savings_pct": 96.0,
                "llm_only_cost_savings_pct": 97.0,
                "graphrag_latency_reduction_pct": 79.0,
                "llm_only_latency_reduction_pct": 80.0,
                "accuracy_graphrag": True,
                "accuracy_llm_only": False,
                "accuracy_baseline": False,
                "hallucination_rate_baseline": 0.23,
                "hallucination_rate_graphrag": 0.02,
                "hallucination_rate_llm_only": 0.15,
                "baseline_cost_usd": 0.0092,
                "graphrag_cost_usd": 0.0003,
                "llm_only_tokens": 300
            }
        ]
        
        aggregate = Comparator.aggregate_results(comparisons)
        
        assert "avg_llm_only_token_reduction_pct" in aggregate
        assert aggregate["avg_llm_only_token_reduction_pct"] == 97.0
        assert "avg_llm_only_cost_savings_pct" in aggregate
        assert "llm_only_accuracy_rate" in aggregate
        assert aggregate["llm_only_accuracy_rate"] == 0.0  # 0/1 = 0%
        assert "avg_hallucination_rate_llm_only" in aggregate
        assert aggregate["avg_hallucination_rate_llm_only"] == 0.15
    
    def test_check_accuracy_with_ground_truth(self):
        """Test accuracy checking against ground truth"""
        rca_report = "The root cause is config_change_123 which modified JWT settings"
        ground_truth = {"ground_truth_root_cause": "config_change_123"}
        
        accuracy = Comparator._check_accuracy(rca_report, ground_truth)
        assert accuracy == True
        
        # Test with incorrect report
        wrong_report = "The root cause is deployment_456"
        accuracy = Comparator._check_accuracy(wrong_report, ground_truth)
        assert accuracy == False
    
    def test_empty_aggregate(self):
        """Test aggregating empty list returns empty dict"""
        aggregate = Comparator.aggregate_results([])
        assert aggregate == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
