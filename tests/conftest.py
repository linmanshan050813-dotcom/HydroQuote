"""
Pytest configuration and fixtures for HydroQuote AI tests
"""
import os
import sys
import pytest
from typing import Generator
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.core.config import Settings, get_settings


@pytest.fixture
def test_settings() -> Settings:
    """
    Fixture providing test settings
    """
    return get_settings()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Fixture providing FastAPI test client
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_watson_nlu_response():
    """
    Mock response for Watson NLU API
    """
    return {
        "usage": {
            "text_units": 1,
            "text_characters": 100,
            "features": 1
        },
        "language": "en",
        "entities": [],
        "keywords": []
    }


@pytest.fixture
def sample_project_input():
    """
    Sample project input for testing
    """
    return {
        "customer_input": "Project in Nepal, 50m head, 10 m³/s flow, 2.5MW capacity",
        "customer_details": {
            "company_name": "Nepal Power Ltd",
            "contact_person": "John Doe",
            "email": "john@nepalpower.com"
        },
        "language": "en",
        "include_pi": True
    }

# Made with Bob
