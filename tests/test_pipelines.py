"""
Tests for pipeline modules
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pipelines.baseline import BaselinePipeline
from pipelines.graphrag import GraphRAGPipeline
from pipelines.llm_only import LLMOnlyPipeline


class TestBaselinePipeline:
    """Tests for BaselinePipeline"""
    
    def test_baseline_pipeline_initialization(self):
        """Test baseline pipeline can be initialized"""
        pipeline = BaselinePipeline()
        assert pipeline is not None
        assert hasattr(pipeline, 'prompt_builder')
        assert hasattr(pipeline, 'llm_client')
    
    def test_assemble_context(self, sample_incident_data):
        """Test context assembly"""
        pipeline = BaselinePipeline()
        context = pipeline.assemble_context("test_incident_1", sample_incident_data)
        
        assert isinstance(context, str)
        assert len(context) > 1000  # Should be substantial
        assert "POST-MORTEM REPORT" in context
        assert "SYSTEM LOGS" in context
    
    @patch('pipelines.baseline.GroqClient')
    def test_baseline_run_returns_required_keys(self, mock_groq, sample_incident_data):
        """Test baseline pipeline returns all required keys"""
        # Mock LLM response
        mock_groq.return_value.call_llm.return_value = {
            "response": "Test RCA report",
            "input_tokens": 11500,
            "output_tokens": 200,
            "total_tokens": 11700,
            "latency_ms": 4200
        }
        mock_groq.return_value.calculate_cost.return_value = 0.0092
        
        pipeline = BaselinePipeline()
        result = pipeline.run("test_incident_1", sample_incident_data)
        
        # Check required keys
        assert "pipeline" in result
        assert result["pipeline"] == "baseline"
        assert "incident_id" in result
        assert "rca_report" in result
        assert "total_tokens" in result
        assert "latency_ms" in result
        assert "cost_usd" in result
        assert result["total_tokens"] > 0


class TestGraphRAGPipeline:
    """Tests for GraphRAGPipeline"""
    
    def test_graphrag_pipeline_initialization(self):
        """Test GraphRAG pipeline can be initialized"""
        pipeline = GraphRAGPipeline()
        assert pipeline is not None
        assert hasattr(pipeline, 'graph_queries')
        assert hasattr(pipeline, 'prompt_builder')
        assert hasattr(pipeline, 'llm_client')
    
    @patch('pipelines.graphrag.GraphQueries')
    @patch('pipelines.graphrag.GroqClient')
    @patch('pipelines.graphrag.ResponseVerifier')
    def test_graphrag_run_returns_required_keys(self, mock_verifier, mock_groq, mock_graph, sample_incident_data):
        """Test GraphRAG pipeline returns all required keys"""
        # Mock graph query response
        mock_graph.return_value.get_causal_subgraph.return_value = {
            "nodes": [{"id": "alert_1", "type": "alert"}],
            "edges": []
        }
        mock_graph.return_value.find_similar_incidents.return_value = []
        
        # Mock LLM response
        mock_groq.return_value.call_llm.return_value = {
            "response": "Test GraphRAG RCA report",
            "input_tokens": 380,
            "output_tokens": 150,
            "total_tokens": 530,
            "latency_ms": 740
        }
        mock_groq.return_value.calculate_cost.return_value = 0.0003
        
        # Mock verifier response
        mock_verifier.return_value.detect_hallucinations.return_value = {
            "hallucination_count": 0,
            "hallucination_rate": 0.0,
            "hallucinated_entities": []
        }
        
        pipeline = GraphRAGPipeline()
        result = pipeline.run("test_incident_1", sample_incident_data)
        
        # Check required keys
        assert "pipeline" in result
        assert result["pipeline"] == "graphrag"
        assert "incident_id" in result
        assert "rca_report" in result
        assert "total_tokens" in result
        assert "latency_ms" in result
        assert "cost_usd" in result
        assert "hallucination_count" in result
        assert "hallucination_rate" in result
        assert result["total_tokens"] > 0
        assert result["total_tokens"] < 1000  # Should be much smaller than baseline


class TestLLMOnlyPipeline:
    """Tests for LLMOnlyPipeline"""
    
    def test_llm_only_pipeline_initialization(self):
        """Test LLM-only pipeline can be initialized"""
        pipeline = LLMOnlyPipeline()
        assert pipeline is not None
        assert hasattr(pipeline, 'llm_client')
    
    def test_build_prompt(self, sample_incident_data):
        """Test prompt building from raw alert JSON"""
        pipeline = LLMOnlyPipeline()
        prompt = pipeline.build_prompt(sample_incident_data)
        
        assert isinstance(prompt, str)
        assert "ALERT INFORMATION" in prompt
        assert sample_incident_data["alert_name"] in prompt
        assert "root cause analysis" in prompt.lower()
    
    @patch('pipelines.llm_only.GroqClient')
    def test_llm_only_run_returns_required_keys(self, mock_groq, sample_incident_data):
        """Test LLM-only pipeline returns all required keys"""
        # Mock LLM response
        mock_groq.return_value.call_llm.return_value = {
            "response": "Test LLM-only RCA report",
            "input_tokens": 250,
            "output_tokens": 100,
            "total_tokens": 350,
            "latency_ms": 800
        }
        mock_groq.return_value.calculate_cost.return_value = 0.00028
        
        pipeline = LLMOnlyPipeline()
        result = pipeline.run("test_incident_1", sample_incident_data)
        
        # Check required keys
        assert "pipeline" in result
        assert result["pipeline"] == "llm_only"
        assert "incident_id" in result
        assert "rca_report" in result
        assert "prompt_tokens" in result
        assert "completion_tokens" in result
        assert "total_tokens" in result
        assert "latency_ms" in result
        assert "cost_usd" in result
        assert result["total_tokens"] > 0
        assert result["total_tokens"] < 500  # Should be minimal


class TestPipelineIntegration:
    """Integration tests for pipelines"""
    
    @patch('pipelines.baseline.GroqClient')
    @patch('pipelines.graphrag.GraphQueries')
    @patch('pipelines.graphrag.GroqClient')
    @patch('pipelines.llm_only.GroqClient')
    def test_all_pipelines_return_comparable_results(self, mock_llm_groq, mock_graph_groq, 
                                                     mock_graph, mock_base_groq, sample_incident_data):
        """Test all three pipelines return results that can be compared"""
        # Mock responses for all pipelines
        mock_base_groq.return_value.call_llm.return_value = {
            "response": "Baseline RCA", "input_tokens": 11500, "output_tokens": 200,
            "total_tokens": 11700, "latency_ms": 4200
        }
        mock_base_groq.return_value.calculate_cost.return_value = 0.0092
        
        mock_graph.return_value.get_causal_subgraph.return_value = {"nodes": [], "edges": []}
        mock_graph.return_value.find_similar_incidents.return_value = []
        mock_graph_groq.return_value.call_llm.return_value = {
            "response": "GraphRAG RCA", "input_tokens": 380, "output_tokens": 150,
            "total_tokens": 530, "latency_ms": 740
        }
        mock_graph_groq.return_value.calculate_cost.return_value = 0.0003
        
        mock_llm_groq.return_value.call_llm.return_value = {
            "response": "LLM-only RCA", "input_tokens": 250, "output_tokens": 100,
            "total_tokens": 350, "latency_ms": 800
        }
        mock_llm_groq.return_value.calculate_cost.return_value = 0.00028
        
        # Run all pipelines
        baseline = BaselinePipeline()
        graphrag = GraphRAGPipeline()
        llm_only = LLMOnlyPipeline()
        
        baseline_result = baseline.run("test_incident_1", sample_incident_data)
        graphrag_result = graphrag.run("test_incident_1", sample_incident_data)
        llm_only_result = llm_only.run("test_incident_1", sample_incident_data)
        
        # All should have comparable keys
        required_keys = ["pipeline", "incident_id", "rca_report", "total_tokens", "latency_ms", "cost_usd"]
        for result in [baseline_result, graphrag_result, llm_only_result]:
            for key in required_keys:
                assert key in result
        
        # Token counts should be in expected ranges
        assert baseline_result["total_tokens"] > 10000
        assert graphrag_result["total_tokens"] < 1000
        assert llm_only_result["total_tokens"] < 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
