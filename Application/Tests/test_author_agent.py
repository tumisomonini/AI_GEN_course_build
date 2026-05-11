import pytest
from unittest.mock import Mock, patch, AsyncMock
from dotenv import load_dotenv
load_dotenv()
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from Application.Agents.Author_agent import AuthorAgent
from Domain.course import Chapter

@pytest.fixture
def mock_manager():
    manager = Mock()
    manager.astra = Mock()
    manager.astra.vector_store = Mock()
    manager.pg = Mock()
    manager.kg = Mock()
    # Mock hybrid_search for the agent's internal retrieval
    manager.hybrid_search.return_value = {
        'pg_courses': [],
        'kg_context': [],
        'vector': ["chunk1", "chunk2"]
    }
    return manager

@pytest.fixture
def mock_openai_client():
    client = Mock()
    completion = Mock()
    completion.choices = [Mock(message=Mock(content="Generated content"))]
    client.chat.completions.create = AsyncMock(return_value=completion)
    return client

@pytest.mark.asyncio
async def test_author_generate_content(mock_manager, mock_openai_client):
    with patch('Application.Agents.Author_agent.AsyncOpenAI', return_value=mock_openai_client):
        author = AuthorAgent(manager=mock_manager)
        author.openai_client = mock_openai_client
        
        chapter = await author.generate_content("Python Basics")
        assert isinstance(chapter, Chapter)
        assert "Generated content" in chapter.content
        mock_openai_client.chat.completions.create.assert_called()

@pytest.mark.asyncio
async def test_author_parallel(mock_manager, mock_openai_client):
    with patch('Application.Agents.Author_agent.AsyncOpenAI', return_value=mock_openai_client):
        author = AuthorAgent(manager=mock_manager)
        author.openai_client = mock_openai_client
        
        topics = ["Python Basics", "Data Structures"]
        chapters = await author.generate_multiple_chapters(topics)
        assert len(chapters) == 2
        for chapter in chapters:
            assert isinstance(chapter, Chapter)
            assert "Generated content" in chapter.content
