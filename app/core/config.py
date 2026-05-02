"""
Configuration management for HydroQuote AI
Loads environment variables securely and provides typed configuration
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # ============================================
    # IBM Watson Natural Language Understanding (REQUIRED)
    # ============================================
    watson_nlu_api_key: str = Field(..., env="WATSON_NLU_API_KEY")
    watson_nlu_url: str = Field(..., env="WATSON_NLU_URL")
    
    # ============================================
    # IBM watsonx.ai Configuration (Optional - for future use)
    # ============================================
    watsonx_api_key: Optional[str] = Field(default=None, env="WATSONX_API_KEY")
    watsonx_project_id: Optional[str] = Field(default=None, env="WATSONX_PROJECT_ID")
    watsonx_url: str = Field(
        default="https://us-south.ml.cloud.ibm.com",
        env="WATSONX_URL"
    )
    watsonx_model: str = Field(
        default="ibm/granite-13b-chat-v2",
        env="WATSONX_MODEL"
    )
    
    # ============================================
    # Application Configuration
    # ============================================
    app_env: str = Field(default="development", env="APP_ENV")
    app_name: str = Field(default="HydroQuote AI", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # ============================================
    # API Security (Optional)
    # ============================================
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    api_key_name: str = Field(default="X-API-Key", env="API_KEY_NAME")
    
    # ============================================
    # CORS Configuration
    # ============================================
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    
    # ============================================
    # Feature Flags
    # ============================================
    enable_pi_download: bool = Field(default=True, env="ENABLE_PI_DOWNLOAD")
    enable_file_logging: bool = Field(default=False, env="ENABLE_FILE_LOGGING")
    enable_swagger_docs: bool = Field(default=True, env="ENABLE_SWAGGER_DOCS")
    
    # ============================================
    # LLM Configuration
    # ============================================
    llm_temperature: float = Field(default=0.0, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, env="LLM_MAX_TOKENS")
    llm_top_p: float = Field(default=1.0, env="LLM_TOP_P")
    
    # ============================================
    # File Storage
    # ============================================
    output_dir: str = Field(default="./outputs", env="OUTPUT_DIR")
    temp_dir: str = Field(default="./temp", env="TEMP_DIR")
    
    @validator("watson_nlu_api_key")
    def validate_nlu_api_key(cls, v):
        """Ensure Watson NLU API key is not the placeholder value"""
        if not v or v == "your_watson_nlu_api_key_here":
            raise ValueError(
                "WATSON_NLU_API_KEY must be set to a valid API key. "
                "Copy .env.example to .env and add your credentials."
            )
        return v
    
    @validator("watson_nlu_url")
    def validate_nlu_url(cls, v):
        """Ensure Watson NLU URL is valid"""
        if not v or not v.startswith("https://"):
            raise ValueError(
                "WATSON_NLU_URL must be a valid HTTPS URL. "
                "Copy .env.example to .env and add your credentials."
            )
        return v
    
    @validator("cors_origins")
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins"""
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.app_env.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.app_env.lower() == "development"


# Global settings instance
# This will be imported throughout the application
settings = Settings()


def get_settings() -> Settings:
    """
    Dependency function for FastAPI to inject settings
    Usage in FastAPI endpoints:
        @app.get("/")
        def read_root(settings: Settings = Depends(get_settings)):
            return {"app_name": settings.app_name}
    """
    return settings

# Made with Bob
