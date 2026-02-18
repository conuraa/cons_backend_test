"""Smoke tests for basic application functionality."""
import pytest


class TestAppImport:
    """Test FastAPI application import."""
    
    @pytest.mark.unit
    def test_import_fastapi_app(self, app):
        """Test that FastAPI app can be imported."""
        from fastapi import FastAPI
        assert app is not None
        assert isinstance(app, FastAPI)
    
    @pytest.mark.unit
    def test_app_has_routes(self, app):
        """Test that app has registered routes."""
        routes = [route.path for route in app.routes]
        assert "/api/health" in routes or "/api/health/" in routes
        assert len(routes) > 5


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    @pytest.mark.unit
    def test_health_endpoint_returns_200(self, client):
        """Test GET /api/health returns 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200
    
    @pytest.mark.unit
    def test_health_endpoint_returns_json(self, client):
        """Test health endpoint returns valid JSON."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data or "service" in data
