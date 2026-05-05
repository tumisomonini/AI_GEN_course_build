import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
import sys
import os
# sys.path.insert(0, os.path.abspath('../../'))  # Fixed with absolute import
from Application.Agents.Reviewer_agent import ReviewerAgent

def _make_client(response_dict):
    client = Mock()
    completion = Mock()
    completion.choices = [Mock(message=Mock(content=json.dumps(response_dict)))]
    client.chat.completions.create = AsyncMock(return_value=completion)
    return client

@pytest.mark.asyncio
async def test_reviewer_validate_content():
    client = _make_client({'accuracy': 0.9, 'depth': 0.8, 'clarity': 0.8, 'feedback': 'Good'})
    reviewer = ReviewerAgent(client)
    result = await reviewer.validate_content_with_llm('test content', 'test topic')
    assert result['semantic_pass'] is True

@pytest.mark.asyncio
async def test_reviewer_safety_check():
    client = _make_client({'is_valid': True, 'is_safe': True, 'reason': 'OK'})
    reviewer = ReviewerAgent(client)
    result = await reviewer.check_intent_and_safety('educational query')
    assert result['is_valid'] is True
    assert result['is_safe'] is True

@pytest.mark.asyncio
async def test_reviewer_route_query():
    client = _make_client({'strategy': 'hybrid', 'confidence': 0.9, 'reason': 'comprehensive'})
    reviewer = ReviewerAgent(client)
    result = reviewer.route_query('chapter generation')
    assert result['strategy'] in ['vector', 'kg', 'hybrid']

@pytest.mark.asyncio
async def test_reviewer_no_client():
    reviewer = ReviewerAgent()
    result = await reviewer.validate_content_with_llm('content', 'topic')
    assert isinstance(result, dict)  # Graceful fallback

