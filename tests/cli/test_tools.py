"""Tests for tools module."""

import pytest
from src.core.tools import TOOLS, format_tool_call_for_display


class TestTools:
    """Tests for tool definitions and utilities."""

    def test_tools_structure(self):
        """Test that tools have correct structure."""
        assert isinstance(TOOLS, list)
        assert len(TOOLS) > 0

        for tool in TOOLS:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_execute_shell_command_tool_exists(self):
        """Test that execute_shell_command tool is defined."""
        tool_names = [t["function"]["name"] for t in TOOLS]
        assert "execute_shell_command" in tool_names

    def test_read_file_tool_exists(self):
        """Test that read_file tool is defined."""
        tool_names = [t["function"]["name"] for t in TOOLS]
        assert "read_file" in tool_names

    def test_write_file_tool_exists(self):
        """Test that write_file tool is defined."""
        tool_names = [t["function"]["name"] for t in TOOLS]
        assert "write_file" in tool_names

    def test_format_shell_command(self):
        """Test formatting shell command for display."""
        result = format_tool_call_for_display(
            "execute_shell_command",
            {
                "command": "ls -la",
                "explanation": "List all files"
            }
        )
        assert "ls -la" in result
        assert "List all files" in result

    def test_format_read_file(self):
        """Test formatting read file for display."""
        result = format_tool_call_for_display(
            "read_file",
            {
                "filepath": "test.txt",
                "reason": "Check contents"
            }
        )
        assert "test.txt" in result
        assert "Check contents" in result

    def test_format_write_file(self):
        """Test formatting write file for display."""
        result = format_tool_call_for_display(
            "write_file",
            {
                "filepath": "output.txt",
                "content": "Hello World",
                "explanation": "Create greeting file"
            }
        )
        assert "output.txt" in result
        assert "Hello World" in result
        assert "Create greeting file" in result

    def test_format_tool_call_for_display_function_exists(self):
        """Test that format_tool_call_for_display function exists."""
        assert callable(format_tool_call_for_display)
