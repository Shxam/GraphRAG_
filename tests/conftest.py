"""
Pytest configuration and fixtures
"""

import pytest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key")
    monkeypatch.setenv("TIGERGRAPH_HOST", "http://localhost")
    monkeypatch.setenv("TIGERGRAPH_USERNAME", "test_user")
    monkeypatch.setenv("TIGERGRAPH_PASSWORD", "test_pass")
    monkeypatch.setenv("TIGERGRAPH_GRAPH_NAME", "TestGraph")
    monkeypatch.setenv("PIPELINE_TIMEOUT_MS", "10000")
    monkeypatch.setenv("LOG_LEVEL", "INFO")


@pytest.fixture
def sample_incident_data():
    """Sample incident data for testing"""
    return {
        "incident_id": "test_incident_1",
        "alert_id": "test_alert_1",
        "alert_name": "High error rate in test-service",
        "severity": "critical",
        "start_time": "2024-01-15T14:33:00Z",
        "service": "test-service",
        "error_type": "critical",
        "component": "test_alert_1"
    }


@pytest.fixture
def sample_pipeline_result():
    """Sample pipeline result for testing"""
    return {
        "pipeline": "test_pipeline",
        "incident_id": "test_incident_1",
        "rca_report": "Test root cause analysis report",
        "total_tokens": 500,
        "input_tokens": 400,
        "output_tokens": 100,
        "latency_ms": 1000,
        "cost_usd": 0.001,
        "hallucination_rate": 0.05
    }


@pytest.fixture
def sample_ground_truth():
    """Sample ground truth data for testing"""
    return {
        "incident_id": "test_incident_1",
        "ground_truth_root_cause": "config_change_123",
        "affected_services": ["service_a", "service_b"],
        "root_cause_type": "configuration"
    }
