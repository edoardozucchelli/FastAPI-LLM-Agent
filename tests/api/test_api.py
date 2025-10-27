"""Tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from src.api.main import app, llm_client


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_llm_response():
    """Mock LLM response."""
    return "This is a mocked response from the LLM"


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root(self, client):
        """Test root endpoint returns correct message."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "FastAPI Agent is running"}


class TestHealthEndpoint:
    """Tests for the health endpoint."""

    def test_health(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestChatEndpoint:
    """Tests for the chat endpoint."""

    def test_chat_success(self, client, mock_llm_response):
        """Test successful chat request."""
        # Mock the LLM client's chat method
        with patch.object(llm_client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_llm_response

            response = client.post(
                "/chat",
                json={"message": "Hello, AI!"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert data["response"] == mock_llm_response

            # Verify the chat method was called with correct arguments
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args
            assert call_args.kwargs["messages"] == [{"role": "user", "content": "Hello, AI!"}]

    def test_chat_with_custom_parameters(self, client, mock_llm_response):
        """Test chat request with custom temperature and max_tokens."""
        with patch.object(llm_client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_llm_response

            response = client.post(
                "/chat",
                json={
                    "message": "Tell me a story",
                    "temperature": 0.8,
                    "max_tokens": 500
                }
            )

            assert response.status_code == 200

            # Verify parameters were passed correctly
            call_args = mock_chat.call_args
            assert call_args.kwargs["temperature"] == 0.8
            assert call_args.kwargs["max_tokens"] == 500

    def test_chat_missing_message(self, client):
        """Test chat request without message field."""
        response = client.post("/chat", json={})
        assert response.status_code == 422  # Validation error

    def test_chat_with_error_response(self, client):
        """Test chat when LLM returns an error."""
        error_message = "Error: Cannot connect to LLM server"

        with patch.object(llm_client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = error_message

            response = client.post(
                "/chat",
                json={"message": "Hello"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["response"] == error_message


class TestLifespan:
    """Tests for application lifespan management."""

    def test_lifespan_closes_client(self):
        """Test that the lifespan context manager closes the LLM client."""
        with patch.object(llm_client, 'close', new_callable=AsyncMock) as mock_close:
            # Create a test client which triggers lifespan events
            with TestClient(app):
                pass  # Client created and closed

            # Verify close was called
            mock_close.assert_called_once()
