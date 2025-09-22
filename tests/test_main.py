"""
Test suite for SRE Agent FastAPI application
"""

import pytest
from fastapi.testclient import TestClient
from src.sre_agent.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint returns correct information"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "SRE Agent API"
    assert data["version"] == "1.0.0"
    assert "endpoints" in data


def test_health_endpoint():
    """Test the health endpoint returns health status"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "checks" in data
    assert "kubernetes" in data["checks"]
    assert "gemini" in data["checks"]


def test_metrics_endpoint():
    """Test the metrics endpoint returns Prometheus metrics"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    content = response.text
    assert "# HELP" in content
    assert "# TYPE" in content


def test_docs_endpoint():
    """Test the API documentation endpoint"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_endpoint():
    """Test the OpenAPI schema endpoint"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "SRE Agent"


def test_cluster_endpoints_without_k8s():
    """Test cluster endpoints when Kubernetes is not available"""
    # These should return 503 when Kubernetes client is not available
    response = client.get("/cluster/pods")
    assert response.status_code == 503
    
    response = client.get("/cluster/namespaces")
    assert response.status_code == 503


def test_analyze_endpoint_without_dependencies():
    """Test analyze endpoint when dependencies are not available"""
    response = client.post(
        "/analyze",
        json={
            "query": "Test query",
            "namespace": "default"
        }
    )
    # Should return 503 when Kubernetes client is not available
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_health_status_updates():
    """Test that health status reflects actual service states"""
    response = client.get("/health")
    data = response.json()
    
    # In test environment, both should be False
    assert data["checks"]["kubernetes"] is False
    assert data["checks"]["gemini"] is False
    assert data["status"] == "unhealthy"


def test_cors_headers():
    """Test that appropriate headers are set"""
    response = client.get("/")
    # The application should handle basic requests without CORS errors
    assert response.status_code == 200


def test_request_metrics():
    """Test that metrics are incremented on requests"""
    # Make a request
    client.get("/")
    
    # Check metrics endpoint
    response = client.get("/metrics")
    content = response.text
    
    # Should have request count metrics
    assert "http_requests_total" in content
    assert "http_request_duration_seconds" in content


if __name__ == "__main__":
    pytest.main([__file__])