"""
Tests for health check endpoints.
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test cases for health check endpoints."""

    def test_root_endpoint(self, test_client: TestClient):
        """Test the root endpoint returns service information."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "Awasome FastAPI"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert data["environment"] == "test"
        assert "docs_url" in data
        assert "api_url" in data

    def test_health_check_endpoint(self, test_client: TestClient):
        """Test the health check endpoint."""
        response = test_client.get("/api/v1/system/health")
        
        assert response.status_code in [200, 503]
        data = response.json()
        
        # Check required fields
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "uptime" in data
        assert "database" in data
        
        # Validate data types
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["uptime"], (int, float))
        assert isinstance(data["database"], dict)
        
        # Status should be either healthy or unhealthy
        assert data["status"] in ["healthy", "unhealthy"]

    def test_liveness_probe(self, test_client: TestClient):
        """Test the liveness probe endpoint."""
        response = test_client.get("/api/v1/system/health/live")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)

    def test_readiness_probe(self, test_client: TestClient):
        """Test the readiness probe endpoint."""
        response = test_client.get("/api/v1/system/health/ready")
        
        # Can be either ready (200) or not ready (503)
        assert response.status_code in [200, 503]
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] in ["ready", "not ready"]

    def test_service_info_endpoint(self, test_client: TestClient):
        """Test the service information endpoint."""
        response = test_client.get("/api/v1/system/info")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check main sections
        assert "service" in data
        assert "runtime" in data
        assert "api" in data
        assert "database" in data
        assert "features" in data
        
        # Check service info
        service = data["service"]
        assert service["name"] == "Awasome FastAPI"
        assert service["version"] == "1.0.0"
        assert service["environment"] == "test"
        
        # Check runtime info
        runtime = data["runtime"]
        assert "uptime_seconds" in runtime
        assert "start_time" in runtime
        assert "current_time" in runtime
        
        # Check API info
        api = data["api"]
        assert api["version"] == "/api/v1"
        assert api["docs_url"] == "/docs"
        assert api["redoc_url"] == "/redoc"
        
        # Check database info
        database = data["database"]
        assert database["type"] == "CouchDB"
        
        # Check features
        features = data["features"]
        assert isinstance(features["rate_limiting"], bool)
        assert isinstance(features["cors_enabled"], bool)
        assert isinstance(features["security_headers"], bool)
        assert isinstance(features["request_logging"], bool)

    @pytest.mark.asyncio
    async def test_health_check_async(self, async_client: AsyncClient):
        """Test health check endpoint with async client."""
        response = await async_client.get("/api/v1/system/health")
        
        assert response.status_code in [200, 503]
        data = response.json()
        
        assert "status" in data
        assert "database" in data

    def test_health_endpoints_response_time(self, test_client: TestClient):
        """Test that health endpoints respond quickly."""
        import time
        
        endpoints = [
            "/api/v1/system/health/live",
            "/api/v1/system/health/ready",
            "/api/v1/system/health"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = test_client.get(endpoint)
            end_time = time.time()
            
            # Health checks should be fast (under 2 seconds)
            assert end_time - start_time < 2.0
            assert response.status_code in [200, 503]

    def test_health_endpoint_cors(self, test_client: TestClient):
        """Test CORS headers on health endpoints."""
        response = test_client.options("/api/v1/system/health")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 405

    def test_health_endpoint_with_custom_headers(self, test_client: TestClient):
        """Test health endpoint with custom request headers."""
        headers = {
            "User-Agent": "HealthChecker/1.0",
            "Accept": "application/json"
        }
        
        response = test_client.get("/api/v1/system/health", headers=headers)
        assert response.status_code in [200, 503]
        
        # Response should still be JSON
        data = response.json()
        assert isinstance(data, dict)


class TestHealthEndpointEdgeCases:
    """Test edge cases for health endpoints."""

    def test_malformed_requests(self, test_client: TestClient):
        """Test health endpoints handle malformed requests gracefully."""
        # Test with invalid HTTP method where applicable
        endpoints_to_test = [
            "/api/v1/system/health",
            "/api/v1/system/health/live", 
            "/api/v1/system/health/ready",
            "/api/v1/system/info"
        ]
        
        for endpoint in endpoints_to_test:
            # POST should not be allowed (405 Method Not Allowed)
            response = test_client.post(endpoint)
            assert response.status_code == 405

    def test_nonexistent_health_endpoints(self, test_client: TestClient):
        """Test that non-existent health endpoints return 404."""
        response = test_client.get("/api/v1/system/health/nonexistent")
        assert response.status_code == 404

    def test_health_endpoints_during_high_load(self, test_client: TestClient):
        """Test health endpoints remain responsive under load."""
        import concurrent.futures
        import threading
        
        def make_request():
            return test_client.get("/api/v1/system/health/live")
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in futures]
        
        # All requests should succeed
        for response in results:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "alive"