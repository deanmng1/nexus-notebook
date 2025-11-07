"""
Basic API tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert data["status"] == "running"


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data


def test_compare_missing_files():
    """Test compare endpoint with missing files."""
    response = client.post("/api/v1/compare")
    assert response.status_code == 422  # Validation error


def test_job_status_not_found():
    """Test job status for non-existent job."""
    response = client.get("/api/v1/jobs/nonexistent")
    # Should return pending status for unknown jobs
    assert response.status_code in [200, 404]
