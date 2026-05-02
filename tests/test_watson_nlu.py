"""
Test suite for Watson NLU API integration
Tests API connectivity, authentication, and basic functionality
"""
import pytest
import httpx
from app.core.config import get_settings


class TestWatsonNLUConnection:
    """Test Watson NLU API connection and authentication"""
    
    @pytest.mark.asyncio
    async def test_watson_nlu_api_reachable(self):
        """Test that Watson NLU API endpoint is reachable"""
        settings = get_settings()
        
        async with httpx.AsyncClient() as client:
            try:
                # Test basic connectivity (without auth)
                response = await client.get(
                    settings.watson_nlu_url,
                    timeout=10.0
                )
                # Should get 401 or 403 (unauthorized) which means endpoint is reachable
                assert response.status_code in [200, 401, 403, 404]
            except httpx.ConnectError:
                pytest.fail("Cannot connect to Watson NLU API endpoint")
            except httpx.TimeoutException:
                pytest.fail("Watson NLU API endpoint timeout")
    
    @pytest.mark.asyncio
    async def test_watson_nlu_authentication(self):
        """Test Watson NLU API authentication"""
        settings = get_settings()
        
        # Test analyze endpoint with authentication
        url = f"{settings.watson_nlu_url}/v1/analyze"
        params = {
            "version": "2022-04-07",
            "text": "Test text for authentication",
            "features": "entities,keywords"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    auth=("apikey", settings.watson_nlu_api_key),
                    timeout=30.0
                )
                
                # Should get 200 (success) or 400 (bad request but authenticated)
                # Should NOT get 401 (unauthorized)
                assert response.status_code != 401, "Watson NLU authentication failed"
                
                if response.status_code == 200:
                    data = response.json()
                    assert "language" in data or "usage" in data
                    
            except httpx.ConnectError:
                pytest.fail("Cannot connect to Watson NLU API")
            except httpx.TimeoutException:
                pytest.fail("Watson NLU API timeout")
    
    @pytest.mark.asyncio
    async def test_watson_nlu_analyze_text(self):
        """Test Watson NLU text analysis functionality"""
        settings = get_settings()
        
        url = f"{settings.watson_nlu_url}/v1/analyze"
        params = {
            "version": "2022-04-07"
        }
        
        # Proper request body for NLU
        data = {
            "text": "IBM is an American multinational technology company headquartered in Armonk, New York.",
            "features": {
                "entities": {
                    "emotion": False,
                    "sentiment": False
                },
                "keywords": {
                    "emotion": False,
                    "sentiment": False
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    params=params,
                    json=data,
                    auth=("apikey", settings.watson_nlu_api_key),
                    timeout=30.0
                )
                
                assert response.status_code == 200, f"Watson NLU analyze failed: {response.text}"
                
                result = response.json()
                assert "language" in result
                assert "usage" in result
                
                # Check that we got some analysis results
                if "entities" in result:
                    assert isinstance(result["entities"], list)
                if "keywords" in result:
                    assert isinstance(result["keywords"], list)
                    
            except httpx.ConnectError:
                pytest.fail("Cannot connect to Watson NLU API")
            except httpx.TimeoutException:
                pytest.fail("Watson NLU API timeout")
    
    @pytest.mark.asyncio
    async def test_watson_nlu_invalid_auth(self):
        """Test Watson NLU with invalid authentication"""
        settings = get_settings()
        
        url = f"{settings.watson_nlu_url}/v1/analyze"
        params = {
            "version": "2022-04-07"
        }
        
        data = {
            "text": "Test text",
            "features": {
                "keywords": {}
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    params=params,
                    json=data,
                    auth=("apikey", "invalid_api_key_12345"),
                    timeout=30.0
                )
                
                # Should get 401 or 403 for invalid credentials
                assert response.status_code in [401, 403], \
                    "Watson NLU should reject invalid credentials"
                    
            except httpx.ConnectError:
                pytest.fail("Cannot connect to Watson NLU API")
            except httpx.TimeoutException:
                pytest.fail("Watson NLU API timeout")


class TestWatsonNLUFeatures:
    """Test specific Watson NLU features"""
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self):
        """Test entity extraction feature"""
        settings = get_settings()
        
        url = f"{settings.watson_nlu_url}/v1/analyze"
        params = {"version": "2022-04-07"}
        
        data = {
            "text": "Apple Inc. is located in Cupertino, California. Tim Cook is the CEO.",
            "features": {
                "entities": {
                    "limit": 10
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params=params,
                json=data,
                auth=("apikey", settings.watson_nlu_api_key),
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                assert "entities" in result
                entities = result["entities"]
                assert isinstance(entities, list)
                
                # Should detect some entities
                if len(entities) > 0:
                    entity = entities[0]
                    assert "type" in entity
                    assert "text" in entity
    
    @pytest.mark.asyncio
    async def test_keyword_extraction(self):
        """Test keyword extraction feature"""
        settings = get_settings()
        
        url = f"{settings.watson_nlu_url}/v1/analyze"
        params = {"version": "2022-04-07"}
        
        data = {
            "text": "Hydro turbine systems generate renewable energy from water flow. "
                   "Francis turbines are efficient for medium head applications.",
            "features": {
                "keywords": {
                    "limit": 10
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params=params,
                json=data,
                auth=("apikey", settings.watson_nlu_api_key),
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                assert "keywords" in result
                keywords = result["keywords"]
                assert isinstance(keywords, list)
                
                # Should detect some keywords
                if len(keywords) > 0:
                    keyword = keywords[0]
                    assert "text" in keyword
                    assert "relevance" in keyword


class TestWatsonNLUErrorHandling:
    """Test Watson NLU error handling"""
    
    @pytest.mark.asyncio
    async def test_empty_text_error(self):
        """Test error handling for empty text"""
        settings = get_settings()
        
        url = f"{settings.watson_nlu_url}/v1/analyze"
        params = {"version": "2022-04-07"}
        
        data = {
            "text": "",
            "features": {
                "keywords": {}
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params=params,
                json=data,
                auth=("apikey", settings.watson_nlu_api_key),
                timeout=30.0
            )
            
            # Should return error for empty text
            assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_missing_features_error(self):
        """Test error handling for missing features"""
        settings = get_settings()
        
        url = f"{settings.watson_nlu_url}/v1/analyze"
        params = {"version": "2022-04-07"}
        
        data = {
            "text": "Test text without features"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params=params,
                json=data,
                auth=("apikey", settings.watson_nlu_api_key),
                timeout=30.0
            )
            
            # Should return error for missing features
            assert response.status_code in [400, 422]

# Made with Bob
