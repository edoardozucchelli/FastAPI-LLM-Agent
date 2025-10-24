"""LLM client wrapper with tool calling support."""

import json
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional

from src.core.llm_client import LLMClient
from src.core.config import config
from src.cli.expert_modes import (
    ExpertMode,
    ResponseMode,
    get_system_prompt,
    get_expert_config
)


class LLMClientWithTools:
    """Extended LLM client with tool calling capabilities."""

    def __init__(
        self,
        base_url: str,
        model: str,
        expert_mode: ExpertMode,
        response_mode: ResponseMode,
        tools: List[Dict[str, Any]]
    ):
        """
        Initialize the LLM client with tools.

        Args:
            base_url: Base URL of the LLM server
            model: Model name
            expert_mode: Expert specialization mode
            response_mode: Response detail mode (quick/full)
            tools: List of tool definitions
        """
        self.base_client = LLMClient(base_url=base_url, model=model, use_instruct=False)
        self.expert_mode = expert_mode
        self.response_mode = response_mode
        self.tools = tools
        self.conversation_history = []
        self._cancel_flag = False

        # Get configuration
        self.config = get_expert_config(expert_mode, response_mode)

        # Generate system prompt
        self.system_prompt = get_system_prompt(expert_mode, response_mode)

    async def close(self):
        """Close the client."""
        await self.base_client.close()

    def set_expert_mode(self, expert_mode: ExpertMode):
        """
        Change expert mode.

        Args:
            expert_mode: New expert mode
        """
        self.expert_mode = expert_mode
        self.config = get_expert_config(expert_mode, self.response_mode)
        self.system_prompt = get_system_prompt(expert_mode, self.response_mode)

        # Update system message in history if it exists
        if self.conversation_history and self.conversation_history[0]["role"] == "system":
            self.conversation_history[0]["content"] = self.system_prompt

    def set_response_mode(self, response_mode: ResponseMode):
        """
        Change response mode.

        Args:
            response_mode: New response mode (quick/full)
        """
        self.response_mode = response_mode
        self.config = get_expert_config(self.expert_mode, response_mode)
        self.system_prompt = get_system_prompt(self.expert_mode, response_mode)

        # Update system message in history if it exists
        if self.conversation_history and self.conversation_history[0]["role"] == "system":
            self.conversation_history[0]["content"] = self.system_prompt

    def cancel_response(self):
        """Cancel ongoing response by stopping the underlying stream."""
        self._cancel_flag = True
        # Also cancel the stream in the base client
        self.base_client.cancel_stream()

    def add_system_message(self):
        """Add system message to conversation if not present."""
        if not self.conversation_history or self.conversation_history[0]["role"] != "system":
            self.conversation_history.insert(0, {
                "role": "system",
                "content": self.system_prompt
            })

    def add_user_message(self, content: str):
        """Add a user message to the conversation."""
        # If this is the first user message, prepend a role reminder
        # (helps with models that don't respect system prompts well)
        is_first_user_message = not any(
            msg["role"] == "user" for msg in self.conversation_history
        )

        if is_first_user_message:
            # Add expert mode reminder in first message
            expert_name = self.config.get("name", "").replace("🐧 ", "").replace("🐍 ", "").replace("🚀 ", "").replace("🗄️ ", "").replace("💬 ", "")
            content = f"[You are {expert_name}] {content}"

        self.conversation_history.append({
            "role": "user",
            "content": content
        })

    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
        """Add an assistant message to the conversation."""
        message = {
            "role": "assistant",
            "content": content
        }
        if tool_calls:
            message["tool_calls"] = tool_calls

        self.conversation_history.append(message)

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str):
        """Add a tool execution result to the conversation."""
        self.conversation_history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })

    async def chat_with_tools(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a chat request with tool support.

        Yields:
            Dict with either:
            - {"type": "text", "content": str}
            - {"type": "tool_call", "name": str, "arguments": dict, "id": str}
            - {"type": "cancelled"} if cancelled
        """
        self.add_system_message()
        self._cancel_flag = False

        # Use config values if not overridden
        if temperature is None:
            temperature = self.config["temperature"]
        if max_tokens is None:
            max_tokens = self.config["max_tokens"]

        response_text = ""
        try:
            async for chunk in self.base_client.chat_stream(
                messages=self.conversation_history,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                # Check for cancellation
                if self._cancel_flag:
                    yield {"type": "cancelled"}
                    return

                response_text += chunk
                yield {"type": "text", "content": chunk}

        except asyncio.CancelledError:
            yield {"type": "cancelled"}
            return

        # Try to parse tool calls from the response
        tool_calls = self._extract_tool_calls(response_text)

        if tool_calls:
            for tool_call in tool_calls:
                yield {
                    "type": "tool_call",
                    "name": tool_call["name"],
                    "arguments": tool_call["arguments"],
                    "id": tool_call.get("id", "call_0")
                }

    def _extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from LLM response.

        This is a simple pattern-based extraction.
        In production, you'd use the LLM's native function calling API.
        """
        tool_calls = []

        # Look for JSON blocks that might be tool calls
        # Pattern: ```json\n{...}\n```
        import re
        json_blocks = re.findall(r'```json\s*\n(.*?)\n```', text, re.DOTALL)

        for block in json_blocks:
            try:
                data = json.loads(block)

                # Check if it looks like a tool call
                if isinstance(data, dict) and "tool" in data and "arguments" in data:
                    tool_calls.append({
                        "name": data["tool"],
                        "arguments": data["arguments"],
                        "id": f"call_{len(tool_calls)}"
                    })
            except json.JSONDecodeError:
                continue

        return tool_calls

    async def chat_simple(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Simple chat without streaming."""
        self.add_system_message()

        # Use config values if not overridden
        if temperature is None:
            temperature = self.config["temperature"]
        if max_tokens is None:
            max_tokens = self.config["max_tokens"]

        response = await self.base_client.chat(
            messages=self.conversation_history,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_history_length(self) -> int:
        """Get the number of messages in history."""
        return len(self.conversation_history)

    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration info."""
        return {
            "expert_mode": self.expert_mode.value,
            "response_mode": self.response_mode.value,
            "temperature": self.config["temperature"],
            "max_tokens": self.config["max_tokens"],
            "name": self.config["name"],
            "icon": self.config["icon"]
        }
