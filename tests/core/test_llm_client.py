"""Tests for LLM client."""

import pytest
import httpx
import json
from unittest.mock import AsyncMock, Mock, patch
from src.core.llm_client import LLMClient


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def llm_client_instruct(mock_httpx_client):
    """Create an LLM client with instruct mode."""
    client = LLMClient(
        base_url="http://localhost:11434",
        model="mistral",
        use_instruct=True
    )
    client.client = mock_httpx_client
    return client


@pytest.fixture
def llm_client_openai(mock_httpx_client):
    """Create an LLM client with OpenAI-compatible mode."""
    client = LLMClient(
        base_url="http://localhost:1234",
        model="gpt-3.5-turbo",
        use_instruct=False
    )
    client.client = mock_httpx_client
    return client


class TestLLMClientInitialization:
    """Tests for LLM client initialization."""

    def test_init_instruct_mode(self):
        """Test initialization in instruct mode."""
        client = LLMClient(
            base_url="http://localhost:11434",
            model="mistral",
            use_instruct=True
        )
        assert client.base_url == "http://localhost:11434"
        assert client.model == "mistral"
        assert client.use_instruct is True
        assert isinstance(client.client, httpx.AsyncClient)

    def test_init_openai_mode(self):
        """Test initialization in OpenAI mode."""
        client = LLMClient(
            base_url="http://localhost:1234",
            model="gpt-3.5-turbo",
            use_instruct=False
        )
        assert client.base_url == "http://localhost:1234"
        assert client.model == "gpt-3.5-turbo"
        assert client.use_instruct is False


class TestLLMClientChat:
    """Tests for chat functionality."""

    @pytest.mark.asyncio
    async def test_chat_instruct_mode_success(self, llm_client_instruct, mock_httpx_client):
        """Test successful chat in instruct mode."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Hello! How can I help you?"}
        mock_response.raise_for_status = Mock()
        mock_httpx_client.post.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]
        response = await llm_client_instruct.chat(messages)

        assert response == "Hello! How can I help you?"
        mock_httpx_client.post.assert_called_once()

        # Verify the URL and payload
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        assert call_args[1]["json"]["model"] == "mistral"
        assert "[INST]" in call_args[1]["json"]["prompt"]

    @pytest.mark.asyncio
    async def test_chat_openai_mode_success(self, llm_client_openai, mock_httpx_client):
        """Test successful chat in OpenAI mode."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from OpenAI!"}}]
        }
        mock_response.raise_for_status = Mock()
        mock_httpx_client.post.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]
        response = await llm_client_openai.chat(messages)

        assert response == "Hello from OpenAI!"

        # Verify the URL and payload
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == "http://localhost:1234/v1/chat/completions"
        assert call_args[1]["json"]["model"] == "gpt-3.5-turbo"
        assert call_args[1]["json"]["messages"] == messages

    @pytest.mark.asyncio
    async def test_chat_with_temperature(self, llm_client_instruct, mock_httpx_client):
        """Test chat with custom temperature."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Response"}
        mock_response.raise_for_status = Mock()
        mock_httpx_client.post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        await llm_client_instruct.chat(messages, temperature=0.8)

        call_args = mock_httpx_client.post.call_args
        assert call_args[1]["json"]["temperature"] == 0.8

    @pytest.mark.asyncio
    async def test_chat_with_max_tokens(self, llm_client_instruct, mock_httpx_client):
        """Test chat with custom max_tokens."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Response"}
        mock_response.raise_for_status = Mock()
        mock_httpx_client.post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        await llm_client_instruct.chat(messages, max_tokens=500)

        call_args = mock_httpx_client.post.call_args
        assert call_args[1]["json"]["num_predict"] == 500

    @pytest.mark.asyncio
    async def test_chat_connection_error(self, llm_client_instruct, mock_httpx_client):
        """Test chat with connection error."""
        mock_httpx_client.post.side_effect = httpx.ConnectError("Connection failed")

        messages = [{"role": "user", "content": "Test"}]
        response = await llm_client_instruct.chat(messages)

        assert "Cannot connect to LLM server" in response
        assert "http://localhost:11434" in response

    @pytest.mark.asyncio
    async def test_chat_timeout_error(self, llm_client_instruct, mock_httpx_client):
        """Test chat with timeout error."""
        mock_httpx_client.post.side_effect = httpx.TimeoutException("Timeout")

        messages = [{"role": "user", "content": "Test"}]
        response = await llm_client_instruct.chat(messages)

        assert "Request to LLM server timed out" in response

    @pytest.mark.asyncio
    async def test_chat_http_status_error(self, llm_client_instruct, mock_httpx_client):
        """Test chat with HTTP status error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        error = httpx.HTTPStatusError(
            "Server error",
            request=Mock(),
            response=mock_response
        )
        mock_httpx_client.post.side_effect = error

        messages = [{"role": "user", "content": "Test"}]
        response = await llm_client_instruct.chat(messages)

        assert "status 500" in response

    @pytest.mark.asyncio
    async def test_chat_parsing_error(self, llm_client_openai, mock_httpx_client):
        """Test chat with malformed response."""
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "structure"}
        mock_response.raise_for_status = Mock()
        mock_httpx_client.post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        response = await llm_client_openai.chat(messages)

        assert "Error parsing LLM response" in response


class TestLLMClientClose:
    """Tests for client cleanup."""

    @pytest.mark.asyncio
    async def test_close(self, llm_client_instruct, mock_httpx_client):
        """Test closing the client."""
        await llm_client_instruct.close()
        mock_httpx_client.aclose.assert_called_once()


class TestLLMClientStreaming:
    """Tests for streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_instruct_mode(self, llm_client_instruct, mock_httpx_client):
        """Test streaming in instruct mode."""
        # Mock streaming response
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()

        # Simulate streaming lines
        async def mock_aiter_lines():
            yield json.dumps({"response": "Hello", "done": False})
            yield json.dumps({"response": " there", "done": False})
            yield json.dumps({"response": "!", "done": True})

        mock_response.aiter_lines = mock_aiter_lines
        mock_httpx_client.stream.return_value.__aenter__.return_value = mock_response

        messages = [{"role": "user", "content": "Hi"}]
        chunks = []
        async for chunk in llm_client_instruct.chat_stream(messages):
            chunks.append(chunk)

        assert chunks == ["Hello", " there", "!"]

    @pytest.mark.asyncio
    async def test_stream_openai_mode(self, llm_client_openai, mock_httpx_client):
        """Test streaming in OpenAI mode."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()

        # Simulate SSE format
        async def mock_aiter_lines():
            yield "data: " + json.dumps({"choices": [{"delta": {"content": "Hello"}}]})
            yield "data: " + json.dumps({"choices": [{"delta": {"content": " world"}}]})
            yield "data: [DONE]"

        mock_response.aiter_lines = mock_aiter_lines
        mock_httpx_client.stream.return_value.__aenter__.return_value = mock_response

        messages = [{"role": "user", "content": "Hi"}]
        chunks = []
        async for chunk in llm_client_openai.chat_stream(messages):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_with_error(self, llm_client_instruct, mock_httpx_client):
        """Test streaming with HTTP error."""
        mock_httpx_client.stream.side_effect = httpx.HTTPError("Stream error")

        messages = [{"role": "user", "content": "Hi"}]
        chunks = []
        async for chunk in llm_client_instruct.chat_stream(messages):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error communicating with LLM" in chunks[0]
