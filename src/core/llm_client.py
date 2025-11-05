"""LLM client for communicating with Ollama or LM Studio."""

import httpx
import json
from typing import AsyncGenerator, Optional
from src.core.config import config
from src.core.logger import get_logger, log_llm_request, log_llm_response

logger = get_logger(__name__)


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

        logger.info(f"LLMClient initialized: base_url={base_url}, model={model}, use_instruct={use_instruct}")

    async def close(self):
        """Close the HTTP client."""
        logger.info("Closing LLM client")
        await self.client.aclose()

    def cancel_stream(self):
        """Cancel the current streaming response."""
        logger.info("Stream cancellation requested")
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
        logger.debug(f"chat() called with {len(messages)} messages")
        log_llm_request(logger, self.model, messages, temperature=temperature, max_tokens=max_tokens)

        if self.use_instruct:
            # Use Ollama's native /api/generate endpoint
            url = f"{self.base_url}/api/generate"

            # Convert messages to instruct format with system prompt
            # Format: <<SYS>>system<</SYS>> [INST] user1 [/INST] assistant1 [INST] user2 [/INST]
            prompt_parts = []
            system_prompt = None

            # Extract system prompt first
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = f"<<SYS>>\n{msg['content']}\n<</SYS>>"
                    break

            # Build conversation
            conversation_parts = []
            for i, msg in enumerate(messages):
                if msg["role"] == "user":
                    # Check if there's an assistant response after this
                    next_msg = messages[i + 1] if i + 1 < len(messages) else None
                    if next_msg and next_msg["role"] == "assistant":
                        # User message + assistant response (closed conversation turn)
                        conversation_parts.append(f"[INST] {msg['content']} [/INST] {next_msg['content']}")
                    else:
                        # User message without response yet (open conversation turn)
                        conversation_parts.append(f"[INST] {msg['content']} [/INST]")
                elif msg["role"] == "assistant":
                    # Skip - already handled with user message
                    continue

            # Combine system prompt and conversation
            if system_prompt:
                prompt_parts.append(system_prompt)

            # Join conversation parts with space (not double newline)
            if conversation_parts:
                prompt_parts.append(" ".join(conversation_parts))

            prompt = "\n\n".join(prompt_parts) if prompt_parts else ""

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

            logger.debug(f"Using instruct mode with prompt: {prompt[:200]}...")
        else:
            # Use OpenAI-compatible endpoint
            url = f"{self.base_url}/v1/chat/completions"

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or config.generation.temperature,
                "max_tokens": max_tokens or config.generation.max_tokens,
            }

            logger.debug(f"Using OpenAI-compatible mode")

        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request payload keys: {list(payload.keys())}")

        try:
            logger.info(f"Sending request to {url}")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if self.use_instruct:
                # Ollama native response format
                response_text = data.get("response", "")
                log_llm_response(logger, response_text, success=True)
                return response_text
            else:
                # OpenAI format
                response_text = data["choices"][0]["message"]["content"]
                log_llm_response(logger, response_text, success=True)
                return response_text
        except httpx.ConnectError as e:
            error_msg = f"Error: Cannot connect to LLM server at {self.base_url}. Is the server running?"
            logger.error(f"Connection error: {e}")
            log_llm_response(logger, error_msg, success=False)
            return error_msg
        except httpx.TimeoutException as e:
            error_msg = f"Error: Request to LLM server timed out at {self.base_url}"
            logger.error(f"Timeout error: {e}")
            log_llm_response(logger, error_msg, success=False)
            return error_msg
        except httpx.HTTPStatusError as e:
            error_msg = f"Error: LLM server returned status {e.response.status_code}: {e.response.text}"
            logger.error(f"HTTP status error: {e.response.status_code}")
            logger.debug(f"Response text: {e.response.text}")
            log_llm_response(logger, error_msg, success=False)
            return error_msg
        except httpx.HTTPError as e:
            error_msg = f"Error communicating with LLM: {type(e).__name__} - {str(e)}"
            logger.error(f"HTTP error: {type(e).__name__} - {str(e)}")
            log_llm_response(logger, error_msg, success=False)
            return error_msg
        except (KeyError, IndexError) as e:
            error_msg = f"Error parsing LLM response: {str(e)}"
            logger.error(f"Parse error: {e}")
            logger.debug(f"Response data: {data}")
            log_llm_response(logger, error_msg, success=False)
            return error_msg

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Send a streaming chat request to the LLM."""
        logger.debug(f"chat_stream() called with {len(messages)} messages")
        log_llm_request(logger, self.model, messages, temperature=temperature, max_tokens=max_tokens, stream=True)

        if self.use_instruct:
            # Use Ollama's /api/generate endpoint with instruct mode
            logger.info("Starting streaming in instruct mode")
            async for chunk in self._stream_generate(messages, temperature, max_tokens):
                yield chunk
        else:
            # Use OpenAI-compatible /v1/chat/completions endpoint
            logger.info("Starting streaming in OpenAI-compatible mode")
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
        # Format: <<SYS>>system<</SYS>> [INST] user1 [/INST] assistant1 [INST] user2 [/INST]
        prompt_parts = []
        system_prompt = None

        # Extract system prompt first
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = f"<<SYS>>\n{msg['content']}\n<</SYS>>"
                break

        # Build conversation
        conversation_parts = []
        for i, msg in enumerate(messages):
            if msg["role"] == "user":
                # Check if there's an assistant response after this
                next_msg = messages[i + 1] if i + 1 < len(messages) else None
                if next_msg and next_msg["role"] == "assistant":
                    # User message + assistant response (closed conversation turn)
                    conversation_parts.append(f"[INST] {msg['content']} [/INST] {next_msg['content']}")
                else:
                    # User message without response yet (open conversation turn)
                    conversation_parts.append(f"[INST] {msg['content']} [/INST]")
            elif msg["role"] == "assistant":
                # Skip - already handled with user message
                continue

        # Combine system prompt and conversation
        if system_prompt:
            prompt_parts.append(system_prompt)

        # Join conversation parts with space (not double newline)
        if conversation_parts:
            prompt_parts.append(" ".join(conversation_parts))

        prompt = "\n\n".join(prompt_parts) if prompt_parts else ""

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

        logger.debug(f"Stream generate prompt: {prompt[:300]}...")
        logger.debug(f"Payload: {payload}")

        self._stream_cancelled = False
        try:
            logger.info(f"Starting stream request to {self.base_url}/api/generate")
            async with self.client.stream("POST", url, json=payload) as response:
                self._current_response = response
                response.raise_for_status()
                async for line in response.aiter_lines():
                    # Check for cancellation
                    if self._stream_cancelled:
                        logger.info("Stream cancelled by user")
                        break

                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                chunk = data["response"]
                                logger.debug(f"Received chunk: {chunk[:50]}...")
                                yield chunk
                            if data.get("done", False):
                                logger.info("Stream completed successfully")
                                break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to decode JSON line: {line[:100]}")
                            continue
        except httpx.HTTPError as e:
            if not self._stream_cancelled:
                error_msg = f"\nError communicating with LLM: {str(e)}"
                logger.error(f"Stream error: {e}")
                yield error_msg
        finally:
            self._current_response = None
            self._stream_cancelled = False
            logger.debug("Stream cleanup completed")

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

        logger.debug(f"OpenAI stream payload: {payload}")

        self._stream_cancelled = False
        try:
            logger.info(f"Starting OpenAI stream request to {url}")
            async with self.client.stream("POST", url, json=payload) as response:
                self._current_response = response
                response.raise_for_status()
                async for line in response.aiter_lines():
                    # Check for cancellation
                    if self._stream_cancelled:
                        logger.info("OpenAI stream cancelled by user")
                        break

                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            logger.info("OpenAI stream completed successfully")
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    logger.debug(f"Received OpenAI chunk: {content[:50]}...")
                                    yield content
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to decode OpenAI JSON: {data_str[:100]}")
                            continue
        except httpx.HTTPError as e:
            if not self._stream_cancelled:
                error_msg = f"\nError communicating with LLM: {str(e)}"
                logger.error(f"OpenAI stream error: {e}")
                yield error_msg
        finally:
            self._current_response = None
            self._stream_cancelled = False
            logger.debug("OpenAI stream cleanup completed")
