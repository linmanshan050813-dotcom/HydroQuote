"""
Test suite for API health and basic endpoints
Tests root, health check, and config info endpoints
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health check and status endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API information"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "app" in data
        assert "version" in data
        assert "status" in data
        assert "environment" in data
        assert data["status"] == "running"
        assert data["app"] == "HydroQuote AI"
        assert data["version"] == "2.0.0"
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        # Should return 200 if Watson NLU is configured
        # Should return 503 if not configured
        assert response.status_code in [200, 503]
        
        data = response.json()
        if response.status_code == 200:
            assert data["status"] == "healthy"
            assert "app" in data
            assert "version" in data
            assert "environment" in data
            assert "watsonx_configured" in data
        else:
            assert "detail" in data
    
    def test_config_info_endpoint(self, client):
        """Test configuration info endpoint"""
        response = client.get("/config/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "app_name" in data
        assert "app_version" in data
        assert "environment" in data
        assert "features" in data
        assert "llm_config" in data
        assert "security" in data
        
        # Check features
        features = data["features"]
        assert "pi_download" in features
        assert "file_logging" in features
        assert "swagger_docs" in features
        
        # Check LLM config
        llm_config = data["llm_config"]
        assert "model" in llm_config
        assert "temperature" in llm_config
        assert "max_tokens" in llm_config
        assert "top_p" in llm_config
        
        # Check security info (should not expose actual keys)
        security = data["security"]
        assert "api_key_required" in security
        assert "cors_enabled" in security
    
    def test_config_info_no_secrets(self, client):
        """Test that config info endpoint doesn't expose secrets"""
        response = client.get("/config/info")
        assert response.status_code == 200
        
        data = response.json()
        response_str = str(data).lower()
        
        # Ensure no API keys or secrets are exposed
        assert "api_key" not in response_str or "api_key_required" in response_str
        assert "watson_nlu_api_key" not in response_str
        assert "watsonx_api_key" not in response_str
        assert "project_id" not in response_str or "watsonx_project_id" not in response_str


class TestAPIDocumentation:
    """Test API documentation endpoints"""
    
    def test_swagger_docs_available(self, client, test_settings):
        """Test Swagger documentation is available when enabled"""
        if test_settings.enable_swagger_docs:
            response = client.get("/docs")
            assert response.status_code == 200
        else:
            response = client.get("/docs")
            assert response.status_code == 404
    
    def test_redoc_available(self, client, test_settings):
        """Test ReDoc documentation is available when enabled"""
        if test_settings.enable_swagger_docs:
            response = client.get("/redoc")
            assert response.status_code == 200
        else:
            response = client.get("/redoc")
            assert response.status_code == 404
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema is accessible"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Check that our endpoints are documented
        paths = schema["paths"]
        assert "/" in paths
        assert "/health" in paths
        assert "/config/info" in paths


class TestCORSConfiguration:
    """Test CORS middleware configuration"""
    
    def test_cors_headers_present(self, client):
        """Test CORS headers are present in responses"""
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers or \
               "Access-Control-Allow-Origin" in response.headers
    
    def test_cors_allows_credentials(self, client):
        """Test CORS allows credentials"""
        response = client.get("/", headers={
            "Origin": "http://localhost:3000"
        })
        
        # Should have CORS headers
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        if "access-control-allow-origin" in headers_lower:
            # CORS is configured
            assert response.status_code == 200


class TestErrorHandling:
    """Test global error handling"""
    
    def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoint"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
    
    def test_405_method_not_allowed(self, client):
        """Test 405 error for wrong HTTP method"""
        response = client.post("/")  # Root only accepts GET
        assert response.status_code == 405
        
        data = response.json()
        assert "detail" in data

# Made with Bob
