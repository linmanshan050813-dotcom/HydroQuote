"""
HydroQuote AI - Main Application Entry Point
FastAPI application with secure configuration management
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Union

from app.core.config import get_settings, Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """
    Application factory pattern
    Creates and configures the FastAPI application
    """
    settings = get_settings()
    
    # Create FastAPI app with conditional docs
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Database-free LLM-powered hydro turbine quotation system",
        docs_url="/docs" if settings.enable_swagger_docs else None,
        redoc_url="/redoc" if settings.enable_swagger_docs else None,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Log startup information (without sensitive data)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info(f"API Port: {settings.api_port}")
    logger.info(f"Watsonx Model: {settings.watsonx_model}")
    logger.info(f"CORS Origins: {settings.cors_origins}")
    
    # NEVER log sensitive information
    # ❌ DON'T: logger.info(f"API Key: {settings.watsonx_api_key}")
    # ✅ DO: logger.info("API Key: [CONFIGURED]")
    logger.info("Watsonx API Key: [CONFIGURED]")
    logger.info("Watsonx Project ID: [CONFIGURED]")
    
    return app


# Create the application instance
app = create_application()


@app.get("/", tags=["Health"])
async def root() -> Dict[str, str]:
    """Root endpoint - API information"""
    settings = get_settings()
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.app_env,
        "docs": "/docs" if settings.enable_swagger_docs else "disabled"
    }


@app.get("/health", tags=["Health"])
async def health_check(settings: Settings = Depends(get_settings)) -> Dict[str, Union[str, bool]]:
    """
    Health check endpoint
    Verifies that the application is running and configured correctly
    """
    try:
        # Check if critical configuration is present (Watson NLU is required)
        if not settings.watson_nlu_api_key or not settings.watson_nlu_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Missing required Watson NLU configuration"
            )
        
        # Watsonx.ai is optional
        watsonx_configured = bool(settings.watsonx_api_key and settings.watsonx_project_id)
        
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "watsonx_configured": watsonx_configured
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@app.get("/config/info", tags=["Configuration"])
async def config_info(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Get non-sensitive configuration information
    NEVER expose API keys or secrets through this endpoint
    """
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.app_env,
        "features": {
            "pi_download": settings.enable_pi_download,
            "file_logging": settings.enable_file_logging,
            "swagger_docs": settings.enable_swagger_docs
        },
        "llm_config": {
            "model": settings.watsonx_model,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "top_p": settings.llm_top_p
        },
        "security": {
            "api_key_required": settings.api_key is not None,
            "cors_enabled": True
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler
    Ensures sensitive information is never leaked in error messages
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # In production, return generic error message
    settings = get_settings()
    if settings.is_production():
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal error occurred"}
        )
    
    # In development, provide more details (but still no secrets)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal error occurred",
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.is_development(),
        log_level=settings.log_level.lower()
    )

# Made with Bob
