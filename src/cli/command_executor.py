"""Command executor with interactive approval flow."""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax

console = Console()


class CommandExecutor:
    """Handles command execution with user approval and modification."""

    def __init__(self, working_directory: Optional[str] = None):
        """Initialize the command executor."""
        self.working_directory = Path(working_directory or Path.cwd())
        self.execution_history = []

    async def execute_with_approval(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        auto_approve: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute a tool call with user approval.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            auto_approve: If True, skip approval prompt

        Returns:
            Tuple of (success: bool, result: Optional[str])
        """
        # Display what we're about to do
        console.print()
        console.print(Panel(
            self._format_tool_display(tool_name, arguments),
            title=f"[bold]Tool: {tool_name}[/bold]",
            border_style="cyan"
        ))

        if not auto_approve:
            # Ask for approval
            choice = Prompt.ask(
                "\n[bold]Action[/bold]",
                choices=["execute", "modify", "skip", "e", "m", "s"],
                default="execute"
            )

            # Normalize choice
            if choice in ["e", "execute"]:
                pass  # Continue to execution
            elif choice in ["m", "modify"]:
                arguments = await self._modify_arguments(tool_name, arguments)
                if arguments is None:
                    return False, "Modification cancelled"
            elif choice in ["s", "skip"]:
                console.print("[yellow]Skipped[/yellow]")
                return False, "Skipped by user"

        # Execute the tool
        return await self._execute_tool(tool_name, arguments)

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Execute the actual tool."""
        try:
            if tool_name == "execute_shell_command":
                return await self._execute_shell_command(arguments)
            elif tool_name == "read_file":
                return await self._read_file(arguments)
            elif tool_name == "write_file":
                return await self._write_file(arguments)
            else:
                return False, f"Unknown tool: {tool_name}"

        except Exception as e:
            console.print(f"[red]Error executing {tool_name}:[/red] {str(e)}")
            return False, str(e)

    async def _execute_shell_command(
        self,
        arguments: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Execute a shell command."""
        command = arguments.get("command", "")
        working_dir = arguments.get("working_directory", self.working_directory)

        console.print(f"\n[dim]Executing in: {working_dir}[/dim]")
        console.print("[bold cyan]Running...[/bold cyan]")

        try:
            # Execute the command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(working_dir)
            )

            stdout, stderr = await process.communicate()

            # Decode output
            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""

            # Display results
            if stdout_text:
                console.print("\n[bold]Output:[/bold]")
                console.print(stdout_text)

            if stderr_text:
                console.print("\n[bold yellow]Stderr:[/bold yellow]")
                console.print(stderr_text)

            success = process.returncode == 0

            if success:
                console.print("[green]✓ Command executed successfully[/green]")
            else:
                console.print(f"[red]✗ Command failed with exit code {process.returncode}[/red]")

            # Save to history
            self.execution_history.append({
                "type": "shell_command",
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text
            })

            result = f"Exit code: {process.returncode}\nStdout:\n{stdout_text}\nStderr:\n{stderr_text}"
            return success, result

        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            return False, str(e)

    async def _read_file(self, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Read a file."""
        filepath = arguments.get("filepath", "")
        path = Path(filepath)

        try:
            if not path.exists():
                console.print(f"[red]File not found:[/red] {filepath}")
                return False, f"File not found: {filepath}"

            content = path.read_text()

            # Display the file with syntax highlighting
            console.print(f"\n[bold]File: {filepath}[/bold] ({len(content)} chars)")

            # Try to detect language for syntax highlighting
            suffix = path.suffix.lstrip('.')
            if suffix:
                syntax = Syntax(content, suffix, theme="monokai", line_numbers=True)
                console.print(syntax)
            else:
                console.print(content)

            console.print(f"\n[green]✓ File read successfully[/green]")

            return True, content

        except Exception as e:
            console.print(f"[red]Error reading file:[/red] {str(e)}")
            return False, str(e)

    async def _write_file(self, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Write to a file."""
        filepath = arguments.get("filepath", "")
        content = arguments.get("content", "")
        path = Path(filepath)

        try:
            # Check if file exists
            exists = path.exists()
            if exists:
                console.print(f"[yellow]⚠ File exists:[/yellow] {filepath}")
                if not Confirm.ask("Overwrite?", default=False):
                    return False, "User cancelled overwrite"

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            path.write_text(content)

            action = "Updated" if exists else "Created"
            console.print(f"[green]✓ {action} file:[/green] {filepath}")

            return True, f"{action} {filepath}"

        except Exception as e:
            console.print(f"[red]Error writing file:[/red] {str(e)}")
            return False, str(e)

    async def _modify_arguments(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Allow user to modify tool arguments."""
        console.print("\n[bold]Modify arguments:[/bold]")

        new_args = arguments.copy()

        if tool_name == "execute_shell_command":
            new_command = Prompt.ask(
                "Command",
                default=arguments.get("command", "")
            )
            if new_command:
                new_args["command"] = new_command

        elif tool_name == "read_file":
            new_filepath = Prompt.ask(
                "File path",
                default=arguments.get("filepath", "")
            )
            if new_filepath:
                new_args["filepath"] = new_filepath

        elif tool_name == "write_file":
            console.print("[yellow]Use your editor to modify file content[/yellow]")
            new_filepath = Prompt.ask(
                "File path",
                default=arguments.get("filepath", "")
            )
            if new_filepath:
                new_args["filepath"] = new_filepath

        return new_args

    def _format_tool_display(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Format tool call for display."""
        if tool_name == "execute_shell_command":
            cmd = arguments.get("command", "")
            explanation = arguments.get("explanation", "")
            wd = arguments.get("working_directory", "")

            result = f"[bold]Command:[/bold] [cyan]{cmd}[/cyan]\n\n"
            result += f"[bold]Explanation:[/bold]\n{explanation}"
            if wd:
                result += f"\n\n[bold]Working Directory:[/bold] {wd}"
            return result

        elif tool_name == "read_file":
            filepath = arguments.get("filepath", "")
            reason = arguments.get("reason", "")
            return f"[bold]File:[/bold] [cyan]{filepath}[/cyan]\n\n[bold]Reason:[/bold]\n{reason}"

        elif tool_name == "write_file":
            filepath = arguments.get("filepath", "")
            content = arguments.get("content", "")
            explanation = arguments.get("explanation", "")

            preview = content[:300] + "..." if len(content) > 300 else content

            result = f"[bold]File:[/bold] [cyan]{filepath}[/cyan]\n\n"
            result += f"[bold]Explanation:[/bold]\n{explanation}\n\n"
            result += f"[bold]Content Preview:[/bold]\n[dim]{preview}[/dim]"
            return result

        return f"Tool: {tool_name}\nArguments: {arguments}"
