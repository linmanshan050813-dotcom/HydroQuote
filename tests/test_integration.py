"""
Integration tests for the complete application
Tests end-to-end workflows and module interactions
"""
import pytest
from fastapi.testclient import TestClient


class TestApplicationIntegration:
    """Test complete application integration"""
    
    def test_app_startup(self, client):
        """Test that application starts successfully"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "running"
    
    def test_health_check_integration(self, client):
        """Test health check with all dependencies"""
        response = client.get("/health")
        
        # Should work if Watson NLU is configured
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "healthy"
            assert data["watsonx_configured"] in [True, False]
        else:
            # If not configured, should return 503
            assert response.status_code == 503
    
    def test_config_and_health_consistency(self, client):
        """Test that config info and health check are consistent"""
        config_response = client.get("/config/info")
        health_response = client.get("/health")
        
        assert config_response.status_code == 200
        config_data = config_response.json()
        
        # Environment should match
        if health_response.status_code == 200:
            health_data = health_response.json()
            assert config_data["environment"] == health_data["environment"]
            assert config_data["app_version"] == health_data["version"]


class TestErrorHandlingIntegration:
    """Test error handling across the application"""
    
    def test_global_exception_handler(self, client):
        """Test that global exception handler works"""
        # Try to trigger an error
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
    
    def test_validation_errors(self, client):
        """Test validation error handling"""
        # This would test validation if we had POST endpoints
        pass


class TestSecurityIntegration:
    """Test security features integration"""
    
    def test_no_sensitive_data_in_responses(self, client):
        """Test that no sensitive data is exposed in any endpoint"""
        endpoints = ["/", "/health", "/config/info"]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code == 200:
                response_text = response.text.lower()
                
                # Check for common sensitive patterns
                assert "api_key" not in response_text or "api_key_required" in response_text
                assert "password" not in response_text
                assert "secret" not in response_text
                assert "token" not in response_text or "max_tokens" in response_text
    
    def test_cors_security(self, client):
        """Test CORS configuration is secure"""
        response = client.get("/config/info")
        assert response.status_code == 200
        
        # CORS should be enabled
        data = response.json()
        assert data["security"]["cors_enabled"] is True

# Made with Bob
