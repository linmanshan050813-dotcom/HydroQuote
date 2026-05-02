# HydroQuote AI - Project Structure

## 📁 Current Organization

```
OIOteam_IBM_hackathon/
├── 📄 Configuration Files
│   ├── .env                      # Environment variables (not in git)
│   ├── .env.example              # Environment template
│   ├── .gitignore                # Git ignore rules
│   ├── requirements.txt          # Python dependencies
│   ├── pytest.ini                # Pytest configuration
│   ├── Dockerfile                # Docker container config
│   └── docker-compose.yml        # Docker compose config
│
├── 📚 Documentation
│   ├── README.md                 # Project overview
│   ├── DEMO_QUICKSTART.md        # Quick start guide
│   ├── FRONTEND_GUIDE.md         # Frontend usage guide
│   ├── TESTING_GUIDE.md          # Testing documentation
│   ├── BUG_REPORT.md             # Bug fixes documentation
│   ├── SECURITY.md               # Security guidelines
│   ├── SETUP_GUIDE.md            # Setup instructions
│   ├── ARCHITECTURE_REDESIGN_PLAN.md  # Architecture docs
│   └── PROJECT_STRUCTURE.md      # This file
│
├── 🚀 Launch Scripts
│   ├── start_backend.py          # Backend launcher (fixed imports)
│   ├── serve_frontend.py         # Frontend server
│   ├── start_demo.bat            # Windows one-click launcher
│   └── run_tests.py              # Test runner
│
├── 🎨 Frontend
│   └── frontend/
│       └── index.html            # Interactive demo dashboard
│
├── 🐍 Application Code
│   └── app/
│       ├── __init__.py           # App initialization
│       ├── main.py               # FastAPI application
│       ├── core/                 # Core functionality
│       │   ├── __init__.py
│       │   └── config.py         # Configuration management
│       ├── api/                  # API endpoints (future)
│       │   └── v1/
│       ├── models/               # Data models (future)
│       ├── services/             # Business logic (future)
│       └── prompts/              # LLM prompts (future)
│
├── 🧪 Tests
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py           # Shared fixtures
│       ├── test_config.py        # Configuration tests (13 tests)
│       ├── test_api_health.py    # API endpoint tests
│       ├── test_watson_nlu.py    # Watson NLU tests (8 tests)
│       └── test_integration.py   # Integration tests
│
└── 📋 Planning Documents
    └── Planning Docs/            # Original planning documents