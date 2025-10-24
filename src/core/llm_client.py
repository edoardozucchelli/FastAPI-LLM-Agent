"""LLM client for communicating with Ollama or LM Studio."""

import httpx
import json
from typing import AsyncGenerator, Optional
from src.core.config import config


class LLMClient:
    """Client for interacting with Ollama/LM Studio API."""

    def __init__(self, base_url: str, model: str, use_instruct: bool = True):
        """Initialize the LLM client.

        Args:
            base_url: The base URL of the LLM server
            model: The model name to use
            use_instruct: If True, use Ollama's /api/generate with instruct format
        """
        self.base_url = base_url
        self.model = model
        self.use_instruct = use_instruct
        self.client = httpx.AsyncClient(timeout=300.0)
        self._current_response = None
        self._stream_cancelled = False

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def cancel_stream(self):
        """Cancel the current streaming response."""
        self._stream_cancelled = True
        # Note: We just set the flag. The stream will check it on next iteration
        # and break out of the loop, which will trigger the context manager cleanup

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a chat request to the LLM."""
        if self.use_instruct:
            # Use Ollama's native /api/generate endpoint
            url = f"{self.base_url}/api/generate"

            # Convert messages to instruct format
            user_message = messages[-1]["content"] if messages else ""
            prompt = f"[INST] {user_message} [/INST]"

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }

            # Add optional parameters
            if temperature is not None:
                payload["temperature"] = temperature
            if max_tokens is not None:
                payload["num_predict"] = max_tokens
        else:
            # Use OpenAI-compatible endpoint
            url = f"{self.base_url}/v1/chat/completions"

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or config.generation.temperature,
                "max_tokens": max_tokens or config.generation.max_tokens,
            }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if self.use_instruct:
                # Ollama native response format
                return data.get("response", "")
            else:
                # OpenAI format
                return data["choices"][0]["message"]["content"]
        except httpx.ConnectError as e:
            return f"Error: Cannot connect to LLM server at {self.base_url}. Is the server running?"
        except httpx.TimeoutException as e:
            return f"Error: Request to LLM server timed out at {self.base_url}"
        except httpx.HTTPStatusError as e:
            return f"Error: LLM server returned status {e.response.status_code}: {e.response.text}"
        except httpx.HTTPError as e:
            return f"Error communicating with LLM: {type(e).__name__} - {str(e)}"
        except (KeyError, IndexError) as e:
            return f"Error parsing LLM response: {str(e)}"

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Send a streaming chat request to the LLM."""
        if self.use_instruct:
            # Use Ollama's /api/generate endpoint with instruct mode
            async for chunk in self._stream_generate(messages, temperature, max_tokens):
                yield chunk
        else:
            # Use OpenAI-compatible /v1/chat/completions endpoint
            async for chunk in self._stream_chat(messages, temperature, max_tokens):
                yield chunk

    async def _stream_generate(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream using Ollama's /api/generate endpoint with instruct format."""
        url = f"{self.base_url}/api/generate"

        # Convert messages to instruct format
        # Last user message is the prompt
        user_message = messages[-1]["content"] if messages else ""
        prompt = f"[INST] {user_message} [/INST]"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }

        # Add optional parameters if provided
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        self._stream_cancelled = False
        try:
            async with self.client.stream("POST", url, json=payload) as response:
                self._current_response = response
                response.raise_for_status()
                async for line in response.aiter_lines():
                    # Check for cancellation
                    if self._stream_cancelled:
                        break

                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPError as e:
            if not self._stream_cancelled:
                yield f"\nError communicating with LLM: {str(e)}"
        finally:
            self._current_response = None
            self._stream_cancelled = False

    async def _stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream using OpenAI-compatible /v1/chat/completions endpoint."""
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or config.generation.temperature,
            "max_tokens": max_tokens or config.generation.max_tokens,
            "stream": True,
        }

        self._stream_cancelled = False
        try:
            async with self.client.stream("POST", url, json=payload) as response:
                self._current_response = response
                response.raise_for_status()
                async for line in response.aiter_lines():
                    # Check for cancellation
                    if self._stream_cancelled:
                        break

                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPError as e:
            if not self._stream_cancelled:
                yield f"\nError communicating with LLM: {str(e)}"
        finally:
            self._current_response = None
            self._stream_cancelled = False
