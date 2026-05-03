"""
Test suite for configuration module
Tests environment variable loading, validation, and settings
"""
import pytest
import os
from app.core.config import Settings, get_settings


class TestConfigurationModule:
    """Test configuration loading and validation"""
    
    def test_settings_instance(self, test_settings):
        """Test that settings instance is created successfully"""
        assert test_settings is not None
        assert isinstance(test_settings, Settings)
    
    def test_watson_nlu_configuration(self, test_settings):
        """Test Watson NLU configuration is loaded"""
        assert test_settings.watson_nlu_api_key is not None
        assert test_settings.watson_nlu_url is not None
        assert test_settings.watson_nlu_url.startswith("https://")
        assert "watson" in test_settings.watson_nlu_url.lower()
    
    def test_app_configuration(self, test_settings):
        """Test application configuration defaults"""
        assert test_settings.app_name == "HydroQuote AI"
        assert test_settings.app_version == "2.0.0"
        assert test_settings.app_env in ["development", "production", "testing"]
        assert test_settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]
        assert test_settings.api_port > 0
        assert test_settings.api_port < 65536
    
    def test_cors_origins_parsing(self, test_settings):
        """Test CORS origins are parsed correctly"""
        assert isinstance(test_settings.cors_origins, list)
        assert len(test_settings.cors_origins) > 0
    
    def test_feature_flags(self, test_settings):
        """Test feature flags are boolean"""
        assert isinstance(test_settings.enable_pi_download, bool)
        assert isinstance(test_settings.enable_file_logging, bool)
        assert isinstance(test_settings.enable_swagger_docs, bool)
    
    def test_llm_configuration(self, test_settings):
        """Test LLM configuration parameters"""
        assert 0.0 <= test_settings.llm_temperature <= 2.0
        assert test_settings.llm_max_tokens > 0
        assert 0.0 <= test_settings.llm_top_p <= 1.0
    
    def test_environment_detection(self, test_settings):
        """Test environment detection methods"""
        if test_settings.app_env.lower() == "development":
            assert test_settings.is_development() is True
            assert test_settings.is_production() is False
        elif test_settings.app_env.lower() == "production":
            assert test_settings.is_production() is True
            assert test_settings.is_development() is False
    
    def test_get_settings_dependency(self):
        """Test get_settings dependency function"""
        settings = get_settings()
        assert settings is not None
        assert isinstance(settings, Settings)
    
    def test_watsonx_optional_configuration(self, test_settings):
        """Test watsonx.ai configuration (optional)"""
        # These may be None if not configured
        if test_settings.watsonx_api_key:
            assert isinstance(test_settings.watsonx_api_key, str)
        if test_settings.watsonx_project_id:
            assert isinstance(test_settings.watsonx_project_id, str)
        assert test_settings.watsonx_url.startswith("https://")
        assert test_settings.watsonx_model is not None


class TestConfigurationValidation:
    """Test configuration validation rules"""
    
    def test_invalid_watson_nlu_api_key(self, monkeypatch):
        """Test validation fails with invalid Watson NLU API key"""
        monkeypatch.setenv("WATSON_NLU_API_KEY", "your_watson_nlu_api_key_here")
        monkeypatch.setenv("WATSON_NLU_URL", "https://api.watson.cloud.ibm.com")
        
        with pytest.raises(ValueError, match="WATSON_NLU_API_KEY must be set"):
            Settings()
    
    def test_invalid_watson_nlu_url(self, monkeypatch):
        """Test validation fails with invalid Watson NLU URL"""
        monkeypatch.setenv("WATSON_NLU_API_KEY", "valid_key_12345")
        monkeypatch.setenv("WATSON_NLU_URL", "http://insecure.url.com")
        
        with pytest.raises(ValueError, match="WATSON_NLU_URL must be a valid HTTPS URL"):
            Settings()
    
    def test_cors_origins_wildcard(self, monkeypatch):
        """Test CORS origins wildcard parsing"""
        monkeypatch.setenv("WATSON_NLU_API_KEY", "valid_key_12345")
        monkeypatch.setenv("WATSON_NLU_URL", "https://api.watson.cloud.ibm.com")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        
        settings = Settings()
        assert settings.cors_origins == ["*"]
    
    def test_cors_origins_multiple(self, monkeypatch):
        """Test CORS origins multiple values parsing"""
        monkeypatch.setenv("WATSON_NLU_API_KEY", "valid_key_12345")
        monkeypatch.setenv("WATSON_NLU_URL", "https://api.watson.cloud.ibm.com")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,https://example.com")
        
        settings = Settings()
        assert len(settings.cors_origins) == 2
        assert "http://localhost:3000" in settings.cors_origins
        assert "https://example.com" in settings.cors_origins

# Made with Bob
