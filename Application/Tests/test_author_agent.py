import pytest
from unittest.mock import Mock, patch, MagicMock
from Application.Agents.Author_agent import AuthorAgent
from sentence_transformers import SentenceTransformer

@pytest.fixture
def mock_astra():
    astra = Mock()
    astra.query.return_value = [{"text": "chunk1"}, {"text": "chunk2"}]
    return astra

@pytest.fixture
def mock_openai_client():
    client = Mock()
    completion = Mock()
    completion.choices = [Mock(message=Mock(content="Generated content"))]
    client.chat.completions.create.return_value = completion
    return client

def test_author_generate_content(mock_astra, mock_openai_client):
    with patch('sentence_transformers.SentenceTransformer') as mock_embed:
        mock_model = Mock()
        mock_model.encode.return_value = [0.1] * 384
        mock_embed.return_value = mock_model
        
        author = AuthorAgent(mock_astra, "fake_key")
        author.openai_client = mock_openai_client
        
        content = author.generate_content("Python Basics")
        assert "Generated content" in content
        mock_openai_client.chat.completions.create.assert_called_once()
