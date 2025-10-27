"""Tests for input handler."""

import pytest
from src.cli.input_handler import InputHandler


class TestInputHandler:
    """Tests for InputHandler class."""

    def test_init(self):
        """Test InputHandler initialization."""
        handler = InputHandler()
        assert handler is not None
        assert handler.multiline_delimiters == ['"""', "'''", "```"]

    def test_parse_command_from_input_with_bash_block(self):
        """Test parsing bash command from markdown code block."""
        handler = InputHandler()

        text = """
Here's a command:
```bash
ls -la
```
"""
        result = handler.parse_command_from_input(text)
        assert result == "ls -la"

    def test_parse_command_from_input_with_sh_block(self):
        """Test parsing shell command from markdown code block."""
        handler = InputHandler()

        text = """
```sh
git status
```
"""
        result = handler.parse_command_from_input(text)
        assert result == "git status"

    def test_parse_command_from_input_no_command(self):
        """Test when no command is present."""
        handler = InputHandler()

        text = "Just regular text without commands"
        result = handler.parse_command_from_input(text)
        assert result is None

    def test_parse_command_from_input_multiline_command(self):
        """Test parsing multiline command."""
        handler = InputHandler()

        text = """
```bash
echo "Hello"
echo "World"
```
"""
        result = handler.parse_command_from_input(text)
        assert "echo" in result
        assert "Hello" in result


# Add more tests for file ingestion when we can mock file system
