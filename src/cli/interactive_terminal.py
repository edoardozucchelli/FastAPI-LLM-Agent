"""Interactive terminal for the agent CLI."""

import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import IntPrompt, Prompt

from src.core.config import config
from src.cli.input_handler import InputHandler
from src.cli.command_executor import CommandExecutor
from src.cli.command_parser import CommandParser, format_command_menu
from src.cli.llm_client_wrapper import LLMClientWithTools
from src.cli.expert_modes import (
    ExpertMode,
    ResponseMode,
    get_expert_display_info,
    get_response_mode_display_info
)
from src.core.tools import TOOLS

console = Console()


class InteractiveCLI:
    """Interactive CLI with command execution and file ingestion support."""

    def __init__(self, base_url: str = None, model: str = None):
        """Initialize the interactive CLI."""
        self.input_handler = InputHandler()
        self.command_executor = CommandExecutor()
        self.command_parser = CommandParser()
        self.auto_approve = False
        self.llm_client = None
        self.base_url = base_url
        self.model = model

    def _select_server_and_model(self):
        """Interactive selection of server and model."""
        console.print("\n[bold cyan]🖥️  Select LLM Server[/bold cyan]\n")

        # Display server options
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Server Name")
        table.add_column("URL")
        table.add_column("Available Models")

        for idx, server in enumerate(config.servers, 1):
            models_str = ", ".join(server.models[:3])
            if len(server.models) > 3:
                models_str += f" (+{len(server.models) - 3} more)"
            table.add_row(str(idx), server.name, server.url, models_str)

        console.print(table)

        # Get server selection
        while True:
            try:
                server_idx = IntPrompt.ask("\nSelect server number", default=1)
                if 1 <= server_idx <= len(config.servers):
                    selected_server = config.servers[server_idx - 1]
                    break
                console.print("[red]Invalid selection. Try again.[/red]")
            except (ValueError, KeyboardInterrupt):
                console.print("[red]Invalid input. Try again.[/red]")

        # Display model options
        console.print(f"\n[bold cyan]🤖 Select Model for {selected_server.name}[/bold cyan]\n")

        model_table = Table(show_header=True, header_style="bold magenta")
        model_table.add_column("#", style="dim", width=3)
        model_table.add_column("Model Name")

        for idx, model in enumerate(selected_server.models, 1):
            model_table.add_row(str(idx), model)

        console.print(model_table)

        # Get model selection
        while True:
            try:
                model_idx = IntPrompt.ask("\nSelect model number", default=1)
                if 1 <= model_idx <= len(selected_server.models):
                    selected_model = selected_server.models[model_idx - 1]
                    break
                console.print("[red]Invalid selection. Try again.[/red]")
            except (ValueError, KeyboardInterrupt):
                console.print("[red]Invalid input. Try again.[/red]")

        return selected_server, selected_model

    def _select_expert_mode(self) -> ExpertMode:
        """Interactive selection of expert mode."""
        console.print("\n[bold cyan]🎯 Select Expert Mode[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Expert", style="bold")
        table.add_column("Description")

        expert_info = get_expert_display_info()
        for idx, name, desc in expert_info:
            table.add_row(str(idx), name, desc)

        console.print(table)

        while True:
            try:
                choice = IntPrompt.ask("\nSelect expert mode", default=1)
                if 1 <= choice <= len(expert_info):
                    # Map choice to ExpertMode enum
                    modes = list(ExpertMode)
                    return modes[choice - 1]
                console.print("[red]Invalid selection. Try again.[/red]")
            except (ValueError, KeyboardInterrupt):
                console.print("[red]Invalid input. Try again.[/red]")

    def _select_response_mode(self) -> ResponseMode:
        """Interactive selection of response mode."""
        console.print("\n[bold cyan]💬 Select Response Mode[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Mode", style="bold")
        table.add_column("Description")

        mode_info = get_response_mode_display_info()
        for idx, name, desc in mode_info:
            table.add_row(str(idx), name, desc)

        console.print(table)

        while True:
            try:
                choice = IntPrompt.ask("\nSelect response mode", default=1)
                if choice == 1:
                    return ResponseMode.QUICK
                elif choice == 2:
                    return ResponseMode.FULL
                console.print("[red]Invalid selection. Try again.[/red]")
            except (ValueError, KeyboardInterrupt):
                console.print("[red]Invalid input. Try again.[/red]")

    async def run(self):
        """Run the interactive CLI."""
        # Startup: Server/Model selection
        if self.base_url and self.model:
            server_url = self.base_url
            model_name = self.model
        else:
            server, model_name = self._select_server_and_model()
            server_url = server.url

        # Startup: Expert mode selection
        expert_mode = self._select_expert_mode()

        # Startup: Response mode selection
        response_mode = self._select_response_mode()

        # Initialize LLM client with selected modes
        self.llm_client = LLMClientWithTools(
            base_url=server_url,
            model=model_name,
            expert_mode=expert_mode,
            response_mode=response_mode,
            tools=TOOLS
        )

        # Get config info for display
        config_info = self.llm_client.get_current_config()

        # Show welcome panel
        console.print("\n")
        console.print(Panel.fit(
            f"[bold cyan]🚀 FastAPI Agent CLI[/bold cyan]\n\n"
            f"[bold]Configuration:[/bold]\n"
            f"• Server: {server_url}\n"
            f"• Model: {model_name}\n"
            f"• Expert: {config_info['icon']} {config_info['expert_mode'].title()}\n"
            f"• Response: {'⚡ Quick' if response_mode == ResponseMode.QUICK else '📖 Full'}\n\n"
            f"[bold]Special Commands:[/bold]\n"
            f"• !mode quick|full - Switch response mode\n"
            f"• !expert linux|python|devops|database|general - Switch expert\n"
            f"• !status - Show current configuration\n"
            f"• !clear - Clear conversation history\n"
            f"• !multiline - Enter multi-line input mode\n"
            f"• !help - Show help\n"
            f"• !quit, !exit, !q - Exit\n\n"
            f"[bold]Input Features:[/bold]\n"
            f"• Multi-line mode: !multiline (finish with Ctrl+D)\n"
            f"• Quick multi-line: Use ''' or ``` or \"\"\"\n"
            f"• File ingestion: @filename.txt\n"
            f"• Shell commands: !ls, !pwd, !git status\n"
            f"• Interrupt: Press Ctrl+C during response\n\n"
            f"[dim]Note: Command suggestions only in Linux Expert mode[/dim]",
            title="✨ Welcome",
            border_style="cyan"
        ))

        # Main loop
        try:
            while True:
                try:
                    # Show prompt with color
                    console.print()
                    console.print("[bold green]You[/bold green] ", end="")

                    # Get user input (without color markup in prompt)
                    try:
                        user_input = await self.input_handler.get_input("> ")
                    except EOFError:
                        # Ctrl+D - Exit gracefully
                        console.print("\n[yellow]👋 Goodbye! (Ctrl+D)[/yellow]")
                        break
                    except KeyboardInterrupt:
                        # Ctrl+C at prompt - Show reminder
                        console.print("\n[yellow]Use !quit to exit[/yellow]")
                        continue

                    if not user_input:
                        continue

                    # Handle special commands (start with !)
                    if user_input.startswith("!"):
                        if await self._handle_special_command(user_input):
                            continue
                        else:
                            break  # Exit requested

                    # Add user message to conversation
                    self.llm_client.add_user_message(user_input)

                    # Get LLM response
                    console.print("\n[bold blue]Agent[/bold blue]: ", end="")

                    response_text = ""
                    tool_calls = []
                    was_cancelled = False

                    # Reset cancellation flags before starting new request
                    self.llm_client._cancel_flag = False
                    self.llm_client.base_client._stream_cancelled = False

                    # Create a streaming task
                    async def stream_response():
                        nonlocal response_text, tool_calls, was_cancelled
                        try:
                            async for chunk in self.llm_client.chat_with_tools():
                                if chunk["type"] == "text":
                                    console.print(chunk["content"], end="")
                                    response_text += chunk["content"]
                                elif chunk["type"] == "tool_call":
                                    tool_calls.append(chunk)
                                elif chunk["type"] == "cancelled":
                                    was_cancelled = True
                                    break
                        except asyncio.CancelledError:
                            was_cancelled = True
                            raise

                    stream_task = asyncio.create_task(stream_response())

                    try:
                        await stream_task
                    except KeyboardInterrupt:
                        # User pressed Ctrl+C during streaming
                        self.llm_client.cancel_response()
                        stream_task.cancel()
                        try:
                            await stream_task
                        except asyncio.CancelledError:
                            pass
                        console.print("\n\n[yellow]⚠️  Response interrupted![/yellow]")
                        was_cancelled = True
                    except Exception as e:
                        # Catch any other errors during streaming
                        console.print(f"\n[red]Error during streaming: {e}[/red]")
                        was_cancelled = True

                    console.print()  # Newline after response

                    if was_cancelled:
                        # Don't save incomplete response
                        # Remove the user message we just added since there's no response
                        if self.llm_client.conversation_history and \
                           self.llm_client.conversation_history[-1]["role"] == "user":
                            self.llm_client.conversation_history.pop()
                        continue

                    # Save assistant response
                    self.llm_client.add_assistant_message(response_text)

                    # Parse commands from response - ONLY for Linux expert mode
                    if self.llm_client.expert_mode == ExpertMode.LINUX:
                        command_options = self.command_parser.parse(response_text)

                        if command_options:
                            # Show command menu
                            await self._handle_command_suggestions(command_options)

                    # Execute any tool calls (from JSON blocks)
                    if tool_calls:
                        await self._handle_tool_calls(tool_calls)

                except KeyboardInterrupt:
                    # Catch any other KeyboardInterrupt (safety net)
                    # Specific cases (at prompt, during streaming) are handled above
                    console.print("\n[yellow]Use !quit to exit[/yellow]")
                    continue

        finally:
            if self.llm_client:
                await self.llm_client.close()

    async def _handle_special_command(self, command: str) -> bool:
        """
        Handle special commands starting with !

        Returns:
            True to continue loop, False to exit
        """
        cmd_lower = command.lower().strip()

        # Exit commands
        if cmd_lower in ["!quit", "!exit", "!q"]:
            console.print("\n[yellow]👋 Goodbye![/yellow]")
            return False

        # Clear history
        elif cmd_lower == "!clear":
            self.llm_client.clear_history()
            console.print("[yellow]✓ Conversation history cleared[/yellow]")
            return True

        # Show status
        elif cmd_lower == "!status":
            config_info = self.llm_client.get_current_config()
            console.print(Panel(
                f"[bold]Current Configuration:[/bold]\n\n"
                f"Expert Mode: {config_info['icon']} [cyan]{config_info['expert_mode'].title()}[/cyan]\n"
                f"Response Mode: [cyan]{config_info['response_mode'].title()}[/cyan]\n"
                f"Temperature: [cyan]{config_info['temperature']}[/cyan]\n"
                f"Max Tokens: [cyan]{config_info['max_tokens']}[/cyan]\n"
                f"Messages in history: [cyan]{self.llm_client.get_history_length()}[/cyan]",
                title="Status",
                border_style="blue"
            ))
            return True

        # Change response mode
        elif cmd_lower.startswith("!mode"):
            parts = cmd_lower.split()
            if len(parts) == 2:
                mode = parts[1]
                if mode == "quick":
                    self.llm_client.set_response_mode(ResponseMode.QUICK)
                    console.print("[green]✓ Response mode: ⚡ Quick (concise answers)[/green]")
                elif mode == "full":
                    self.llm_client.set_response_mode(ResponseMode.FULL)
                    console.print("[green]✓ Response mode: 📖 Full (detailed explanations)[/green]")
                else:
                    console.print(f"[red]Unknown mode: {mode}. Use 'quick' or 'full'[/red]")
            else:
                config_info = self.llm_client.get_current_config()
                console.print(f"Current mode: [cyan]{config_info['response_mode']}[/cyan]")
                console.print("Usage: !mode quick|full")
            return True

        # Change expert mode
        elif cmd_lower.startswith("!expert"):
            parts = cmd_lower.split()
            if len(parts) == 2:
                expert = parts[1]
                expert_map = {
                    "linux": ExpertMode.LINUX,
                    "python": ExpertMode.PYTHON,
                    "devops": ExpertMode.DEVOPS,
                    "database": ExpertMode.DATABASE,
                    "general": ExpertMode.GENERAL
                }
                if expert in expert_map:
                    self.llm_client.set_expert_mode(expert_map[expert])
                    # Clear history when switching expert mode to avoid contamination
                    self.llm_client.clear_history()
                    config_info = self.llm_client.get_current_config()

                    # Show system prompt preview when switching
                    system_preview = self.llm_client.system_prompt[:150].replace('\n', ' ')
                    console.print(f"[green]✓ Expert mode: {config_info['icon']} {expert.title()}[/green]")
                    console.print(f"[dim]System: {system_preview}...[/dim]")
                    console.print("[yellow]💡 Conversation history cleared[/yellow]")
                else:
                    console.print(f"[red]Unknown expert: {expert}[/red]")
                    console.print("Available: linux, python, devops, database, general")
            else:
                config_info = self.llm_client.get_current_config()
                console.print(f"Current expert: [cyan]{config_info['expert_mode']}[/cyan]")
                console.print("Usage: !expert linux|python|devops|database|general")
            return True

        # Auto-approve
        elif cmd_lower.startswith("!auto-approve"):
            parts = cmd_lower.split()
            if len(parts) > 1:
                if parts[1] == "on":
                    self.auto_approve = True
                    console.print("[green]✓ Auto-approve enabled (commands execute automatically)[/green]")
                elif parts[1] == "off":
                    self.auto_approve = False
                    console.print("[yellow]✓ Auto-approve disabled (manual approval required)[/yellow]")
            else:
                status = "enabled" if self.auto_approve else "disabled"
                console.print(f"Auto-approve is currently: [bold]{status}[/bold]")
                console.print("Usage: !auto-approve on|off")
            return True

        # Help
        elif cmd_lower == "!help":
            self._show_help()
            return True

        # Multi-line input mode
        elif cmd_lower == "!multiline":
            user_input = await self.input_handler.get_multiline_input()
            if user_input:
                # Add user message to conversation
                self.llm_client.add_user_message(user_input)

                # Get LLM response
                console.print("\n[bold blue]Agent[/bold blue]: ", end="")

                response_text = ""
                tool_calls = []
                was_cancelled = False

                # Reset cancellation flags before starting new request
                self.llm_client._cancel_flag = False
                self.llm_client.base_client._stream_cancelled = False

                # Create a streaming task
                async def stream_response():
                    nonlocal response_text, tool_calls, was_cancelled
                    try:
                        async for chunk in self.llm_client.chat_with_tools():
                            if chunk["type"] == "text":
                                console.print(chunk["content"], end="")
                                response_text += chunk["content"]
                            elif chunk["type"] == "tool_call":
                                tool_calls.append(chunk)
                            elif chunk["type"] == "cancelled":
                                was_cancelled = True
                                break
                    except asyncio.CancelledError:
                        was_cancelled = True
                        raise

                stream_task = asyncio.create_task(stream_response())

                try:
                    await stream_task
                except KeyboardInterrupt:
                    # User pressed Ctrl+C during streaming
                    self.llm_client.cancel_response()
                    stream_task.cancel()
                    try:
                        await stream_task
                    except asyncio.CancelledError:
                        pass
                    console.print("\n\n[yellow]⚠️  Response interrupted![/yellow]")
                    was_cancelled = True
                except Exception as e:
                    # Catch any other errors during streaming
                    console.print(f"\n[red]Error during streaming: {e}[/red]")
                    was_cancelled = True

                if not was_cancelled:
                    console.print()  # New line after response

                    # Handle tool calls if any
                    if tool_calls and not was_cancelled:
                        await self._handle_tool_calls(tool_calls)

            return True

        # Direct shell command execution (like !ls, !pwd, !cd, etc.)
        else:
            # Extract command after the !
            shell_cmd = command[1:].strip()  # Remove the ! prefix
            if shell_cmd:
                console.print(f"[dim]$ {shell_cmd}[/dim]")
                # Execute the command
                import subprocess
                try:
                    result = subprocess.run(
                        shell_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.stdout:
                        console.print(result.stdout.rstrip())
                    if result.stderr:
                        console.print(f"[red]{result.stderr.rstrip()}[/red]")
                except subprocess.TimeoutExpired:
                    console.print("[red]Command timed out (30s limit)[/red]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
            else:
                console.print("[red]Empty command[/red]")
            return True

    async def _handle_command_suggestions(self, command_options):
        """Handle suggested commands from LLM response."""
        # Format and display menu
        menu = format_command_menu(command_options)
        console.print(menu)

        # Get user choice using simple input
        print()  # Use plain print to avoid Rich conflicts

        try:
            choice_input = input("Select command [0]: ").strip()
            choice = choice_input if choice_input else "0"
        except (EOFError, KeyboardInterrupt):
            print()
            console.print("[yellow]Skipped command execution[/yellow]")
            return

        # Parse choice
        try:
            choice_num = int(choice)

            if choice_num == 0:
                console.print("[dim]Skipped command execution[/dim]")
                return

            if 1 <= choice_num <= len(command_options):
                selected = command_options[choice_num - 1]

                # Execute the command
                success, result = await self.command_executor.execute_with_approval(
                    tool_name="execute_shell_command",
                    arguments={
                        "command": selected.command,
                        "explanation": selected.explanation
                    },
                    auto_approve=self.auto_approve
                )

                # Add result to conversation if successful
                if success:
                    self.llm_client.add_tool_result(
                        f"cmd_{choice_num}",
                        "execute_shell_command",
                        result or "Command executed successfully"
                    )
            else:
                console.print("[red]Invalid choice[/red]")

        except ValueError:
            # Check if it's 'm' for modify
            if choice.lower() == 'm':
                console.print("[yellow]Modify command:[/yellow]")
                modified_cmd = Prompt.ask("Enter command")
                if modified_cmd:
                    success, result = await self.command_executor.execute_with_approval(
                        tool_name="execute_shell_command",
                        arguments={
                            "command": modified_cmd,
                            "explanation": "Modified command"
                        },
                        auto_approve=False  # Always ask for modified commands
                    )
            else:
                console.print("[red]Invalid input. Enter a number, 'm' to modify, or 0 to skip[/red]")

    async def _handle_tool_calls(self, tool_calls: list):
        """Handle tool call execution (from JSON blocks)."""
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            arguments = tool_call["arguments"]
            tool_id = tool_call["id"]

            # Execute with approval
            success, result = await self.command_executor.execute_with_approval(
                tool_name=tool_name,
                arguments=arguments,
                auto_approve=self.auto_approve
            )

            # Add tool result to conversation
            result_text = result if result else ("Success" if success else "Failed")
            self.llm_client.add_tool_result(tool_id, tool_name, result_text)

            # Get follow-up response from LLM if successful
            if success:
                console.print("\n[bold blue]Agent[/bold blue]: ", end="")

                response_text = ""
                async for chunk in self.llm_client.chat_with_tools():
                    if chunk["type"] == "text":
                        console.print(chunk["content"], end="")
                        response_text += chunk["content"]

                console.print()
                self.llm_client.add_assistant_message(response_text)

    def _show_help(self):
        """Show help message."""
        help_text = """
# FastAPI Agent CLI Help

## Special Commands

All special commands start with `!`:

- `!quit`, `!exit`, `!q` - Exit the CLI
- `!clear` - Clear conversation history
- `!status` - Show current configuration
- `!mode quick|full` - Switch between quick/full response modes
- `!expert linux|python|devops|database|general` - Switch expert mode
- `!auto-approve on|off` - Toggle automatic command approval
- `!multiline` - Enter dedicated multi-line input mode
- `!help` - Show this help

## Direct Shell Commands

Execute shell commands directly with `!` prefix:

- `!ls` - List files
- `!pwd` - Print working directory
- `!cat file.txt` - Read file
- `!git status` - Git commands
- Any shell command: `!<command>`

## Input Features

### Multi-line Input

**Dedicated Mode (Recommended):**
Type `!multiline` to enter a clean multi-line editor:
```
You > !multiline
📝 Multi-line input mode
Type or paste your text. Press Ctrl+D (Unix) or Ctrl+Z (Windows) on a new line to finish.
... def hello():
...     print("world")
... [Ctrl+D]
✓ Captured 2 lines (35 characters)
```

**Quick Mode:**
Use triple quotes or backticks:
```
You > '''
def hello():
    print("world")
'''
```

### File Ingestion
Use @ to include file contents:
```
You > Review this code @main.py
You > Compare @file1.py and @file2.py
```

Supports:
- Relative paths: `@file.txt`, `@cli/file.py`
- Absolute paths: `@/home/user/file.txt`
- Home expansion: `@~/file.txt`

## Command Suggestions

**Available ONLY in Linux Expert mode** (`!expert linux`)

When the agent suggests shell commands, you'll see a numbered menu:

```
1. ls *.py
   → List Python files

2. find . -name "*.py"
   → Find Python files recursively

0. Do nothing
   → Skip execution

Select command [0-2, or 'm' to modify]:
```

Options:
- Enter a number (1, 2, etc.) to execute that command
- Enter `0` to skip
- Enter `m` to modify the command before executing

## Expert Modes

Each expert mode has specialized knowledge:

- **Linux** 🐧 - Shell commands, system administration
- **Python** 🐍 - Python coding, debugging
- **DevOps** 🚀 - Docker, K8s, CI/CD
- **Database** 🗄️ - SQL, query optimization
- **General** 💬 - Mixed capabilities

## Response Modes

- **Quick** ⚡ - Concise, fast answers
- **Full** 📖 - Detailed explanations

## Keyboard Shortcuts

- `Ctrl+C` during response - Interrupt LLM response
- `Ctrl+C` at prompt - Show reminder to use !quit
- `Ctrl+D` - Exit (alternative to !quit)

## Tips

1. **Start with expert mode** - Choose the right expert for your task
2. **Use quick mode** for simple questions
3. **Use full mode** when you need explanations
4. **Interrupt bad responses** with Ctrl+C
5. **Review commands** before executing (unless auto-approve is on)
"""
        console.print(Markdown(help_text))


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="FastAPI Agent Interactive CLI")
    parser.add_argument("--url", help="LLM base URL (optional)")
    parser.add_argument("--model", help="Model name (optional)")

    args = parser.parse_args()

    cli = InteractiveCLI(base_url=args.url, model=args.model)
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
