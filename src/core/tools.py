"""Tool definitions for LLM function calling."""

from typing import List, Dict, Any


# Tool definitions in OpenAI function calling format
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_shell_command",
            "description": "Execute a shell command on the user's system. Use this when the user asks to perform system operations, file operations, or run commands. Always explain what the command does before suggesting it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute (e.g., 'ls -la', 'git status')"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "A brief explanation of what this command does and why you're suggesting it"
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Optional working directory to execute the command in (defaults to current directory)"
                    }
                },
                "required": ["command", "explanation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use this when you need to examine a file's contents to answer a question or provide suggestions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The path to the file to read"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why you want to read this file"
                    }
                },
                "required": ["filepath", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or update a file with new contents. Use this when the user asks you to create or modify files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "The path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of what changes you're making"
                    }
                },
                "required": ["filepath", "content", "explanation"]
            }
        }
    }
]

# Note: SYSTEM_PROMPT moved to expert_modes.py
# Each expert mode has its own specialized system prompt


def format_tool_call_for_display(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Format a tool call for display to the user."""
    if tool_name == "execute_shell_command":
        cmd = arguments.get("command", "")
        explanation = arguments.get("explanation", "")
        wd = arguments.get("working_directory")

        result = f"[bold cyan]Command:[/bold cyan] {cmd}\n"
        result += f"[bold yellow]Explanation:[/bold yellow] {explanation}"
        if wd:
            result += f"\n[bold]Working Directory:[/bold] {wd}"
        return result

    elif tool_name == "read_file":
        filepath = arguments.get("filepath", "")
        reason = arguments.get("reason", "")
        return f"[bold cyan]Read File:[/bold cyan] {filepath}\n[bold yellow]Reason:[/bold yellow] {reason}"

    elif tool_name == "write_file":
        filepath = arguments.get("filepath", "")
        content = arguments.get("content", "")
        explanation = arguments.get("explanation", "")

        # Show preview of content (first 200 chars)
        preview = content[:200] + "..." if len(content) > 200 else content

        result = f"[bold cyan]Write File:[/bold cyan] {filepath}\n"
        result += f"[bold yellow]Explanation:[/bold yellow] {explanation}\n"
        result += f"[bold]Content Preview:[/bold]\n{preview}"
        return result

    return f"Unknown tool: {tool_name}"
