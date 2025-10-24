"""Enhanced input handler with multi-line support and file ingestion."""

import os
import re
from pathlib import Path
from typing import Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

console = Console()


class InputHandler:
    """Handles user input with support for multi-line input and file references."""

    def __init__(self):
        """Initialize the input handler."""
        self.session = PromptSession(history=InMemoryHistory())
        self.multiline_delimiters = ['"""', "'''", "```"]

    async def get_input(self, prompt: str = "> ") -> Optional[str]:
        """
        Get user input with support for:
        - Single line input
        - Multi-line input (using triple quotes or backticks)
        - File ingestion (using @filename syntax)

        Returns:
            The processed input string, or None if empty input

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C
            EOFError: If user presses Ctrl+D
        """
        user_input = await self.session.prompt_async(prompt)

        if not user_input.strip():
            return None

        # Check for multi-line delimiter at the start
        for delimiter in self.multiline_delimiters:
            if user_input.strip().startswith(delimiter):
                return await self._handle_multiline(user_input, delimiter)

        # Process file references
        return await self._process_file_references(user_input)

    async def get_multiline_input(self) -> Optional[str]:
        """
        Get multi-line input using a dedicated editor mode.
        User can type/paste multiple lines and finish with Ctrl+D (or Ctrl+Z on Windows).

        Returns:
            The complete multi-line input, or None if cancelled

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C
        """
        console.print("[bold cyan]📝 Multi-line input mode[/bold cyan]")
        console.print("[dim]Type or paste your text. Press Ctrl+D (Unix) or Ctrl+Z (Windows) on a new line to finish.[/dim]")
        console.print("[dim]Press Ctrl+C to cancel.[/dim]")
        console.print()

        lines = []

        try:
            while True:
                try:
                    line = await self.session.prompt_async("... ")
                    lines.append(line)
                except EOFError:
                    # Ctrl+D pressed - finish input
                    break

        except KeyboardInterrupt:
            console.print("\n[yellow]Multi-line input cancelled[/yellow]")
            return None

        if not lines:
            return None

        result = "\n".join(lines)

        # Show preview of what was captured
        line_count = len(lines)
        char_count = len(result)
        console.print(f"\n[green]✓[/green] Captured {line_count} lines ({char_count} characters)")

        # Process file references if any
        return await self._process_file_references(result)

    async def _handle_multiline(self, first_line: str, delimiter: str) -> str:
        """Handle multi-line input with a delimiter."""
        lines = [first_line]

        console.print("[dim]Multi-line mode (end with same delimiter)...[/dim]")

        # Remove delimiter from first line if it's only the delimiter
        if first_line.strip() == delimiter:
            lines = []
        else:
            lines[0] = first_line.replace(delimiter, "", 1)

        try:
            while True:
                line = await self.session.prompt_async("... ")

                if delimiter in line:
                    # Found closing delimiter
                    lines.append(line.replace(delimiter, ""))
                    break
                else:
                    lines.append(line)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Multi-line input cancelled[/yellow]")
            return ""

        return "\n".join(lines)

    async def _process_file_references(self, text: str) -> str:
        """
        Process @filename references in the input.

        Syntax: @filename.txt - ingest the entire file
        Example: "Review this code @main.py and suggest improvements"

        Supports:
        - Relative paths: @file.txt, @cli/file.py
        - Absolute paths: @/home/user/file.txt
        - Home expansion: @~/file.txt
        """
        # Find all @filename patterns (improved to catch more cases)
        pattern = r'@([\w\./\-~]+(?:\.\w+)?)'
        matches = list(re.finditer(pattern, text))

        processed_text = text
        file_contents = []

        for match in matches:
            filepath = match.group(1)

            # Try to resolve the file path
            resolved_path = self._resolve_file_path(filepath)

            if resolved_path and resolved_path.exists() and resolved_path.is_file():
                try:
                    content = resolved_path.read_text()

                    # Build a formatted file block
                    file_block = f"\n\n--- File: {filepath} ---\n{content}\n--- End of {filepath} ---\n"
                    file_contents.append(file_block)

                    console.print(f"[green]✓[/green] Loaded file: [cyan]{filepath}[/cyan] ({len(content)} chars)")

                except Exception as e:
                    console.print(f"[red]✗[/red] Error reading {filepath}: {str(e)}")
            else:
                # Show helpful error message with current directory
                cwd = os.getcwd()
                console.print(f"[yellow]⚠[/yellow] File not found: [cyan]{filepath}[/cyan]")
                console.print(f"[dim]   Current directory: {cwd}[/dim]")

                # Suggest possible paths
                suggestions = self._suggest_file_paths(filepath)
                if suggestions:
                    console.print(f"[dim]   Did you mean: {', '.join(suggestions)}[/dim]")

        # Replace @filename references with the actual content
        for match in matches:
            processed_text = processed_text.replace(match.group(0), "", 1)

        # Append all file contents at the end
        if file_contents:
            processed_text = processed_text.strip() + "\n" + "".join(file_contents)

        return processed_text

    def _resolve_file_path(self, filepath: str) -> Optional[Path]:
        """
        Resolve a file path trying multiple strategies.

        Returns:
            Resolved Path object, or None if not found
        """
        # Strategy 1: Expand home directory
        if filepath.startswith('~'):
            path = Path(filepath).expanduser()
            if path.exists():
                return path

        # Strategy 2: Try as absolute path
        path = Path(filepath)
        if path.is_absolute() and path.exists():
            return path

        # Strategy 3: Try as relative to current directory
        if path.exists():
            return path

        # Strategy 4: Try relative to working directory
        cwd = Path.cwd()
        path = cwd / filepath
        if path.exists():
            return path

        return None

    def _suggest_file_paths(self, filepath: str) -> list[str]:
        """
        Suggest possible file paths if the given one doesn't exist.

        Returns:
            List of suggested paths
        """
        suggestions = []
        cwd = Path.cwd()

        # Get filename without path
        filename = Path(filepath).name

        # Search in current directory and immediate subdirectories
        try:
            # Current directory
            for file in cwd.glob(filename):
                if file.is_file():
                    suggestions.append(str(file.relative_to(cwd)))

            # One level deep
            for file in cwd.glob(f"*/{filename}"):
                if file.is_file():
                    suggestions.append(str(file.relative_to(cwd)))

        except Exception:
            pass

        return suggestions[:3]  # Limit to 3 suggestions

    def parse_command_from_input(self, text: str) -> Optional[str]:
        """
        Extract shell command from text if present.
        Looks for code blocks with bash/sh/shell markers.
        """
        # Pattern for ```bash command ```
        bash_pattern = r'```(?:bash|sh|shell)\s*\n(.*?)\n```'
        match = re.search(bash_pattern, text, re.DOTALL)

        if match:
            return match.group(1).strip()

        return None
