"""
Start the HydroQuote AI backend server
This script ensures proper module imports
"""
import sys
import os
import codecs

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now import and run the app
if __name__ == "__main__":
    import uvicorn
    from app.core.config import get_settings
    
    settings = get_settings()
    
    print("=" * 70)
    print("🌊 HydroQuote AI - Backend Server")
    print("=" * 70)
    print(f"\n✓ Starting {settings.app_name} v{settings.app_version}")
    print(f"✓ Environment: {settings.app_env}")
    print(f"✓ API Port: {settings.api_port}")
    print(f"✓ Swagger Docs: {'Enabled' if settings.enable_swagger_docs else 'Disabled'}")
    print(f"\n🌐 API URL: http://localhost:{settings.api_port}")
    print(f"📚 Swagger UI: http://localhost:{settings.api_port}/docs")
    print(f"📖 ReDoc: http://localhost:{settings.api_port}/redoc")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 70)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.is_development(),
        log_level=settings.log_level.lower()
    )

# Made with Bob
