"""
Configuration management for HydroQuote AI
Loads environment variables securely and provides typed configuration
"""
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================
    # IBM Watson Natural Language Understanding (REQUIRED)
    # ============================================
    watson_nlu_api_key: str
    watson_nlu_url: str

    # ============================================
    # IBM watsonx.ai Configuration (Optional - for future use)
    # ============================================
    watsonx_api_key: Optional[str] = None
    watsonx_project_id: Optional[str] = None
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    watsonx_model: str = "ibm/granite-13b-chat-v2"

    # ============================================
    # Application Configuration
    # ============================================
    app_env: str = "development"
    app_name: str = "HydroQuote AI"
    app_version: str = "2.0.0"
    log_level: str = "INFO"
    api_port: int = 8000

    # ============================================
    # API Security (Optional)
    # ============================================
    api_key: Optional[str] = None
    api_key_name: str = "X-API-Key"

    # ============================================
    # CORS Configuration
    # ============================================
    cors_origins: Union[str, List[str]] = "*"

    # ============================================
    # Feature Flags
    # ============================================
    enable_pi_download: bool = True
    enable_file_logging: bool = False
    enable_swagger_docs: bool = True

    # ============================================
    # LLM Configuration
    # ============================================
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2000
    llm_top_p: float = 1.0

    # ============================================
    # File Storage
    # ============================================
    output_dir: str = "./outputs"
    temp_dir: str = "./temp"

    @field_validator("watson_nlu_api_key")
    @classmethod
    def validate_nlu_api_key(cls, v: str) -> str:
        """Ensure Watson NLU API key is not the placeholder value"""
        if not v or v == "your_watson_nlu_api_key_here":
            raise ValueError(
                "WATSON_NLU_API_KEY must be set to a valid API key. "
                "Copy .env.example to .env and add your credentials."
            )
        return v

    @field_validator("watson_nlu_url")
    @classmethod
    def validate_nlu_url(cls, v: str) -> str:
        """Ensure Watson NLU URL is valid"""
        if not v or not v.startswith("https://"):
            raise ValueError(
                "WATSON_NLU_URL must be a valid HTTPS URL. "
                "Copy .env.example to .env and add your credentials."
            )
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins into a list"""
        if isinstance(v, list):
            return v
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in str(v).split(",") if origin.strip()]
        
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
