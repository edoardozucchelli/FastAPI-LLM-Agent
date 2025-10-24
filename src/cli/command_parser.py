"""Parser for extracting shell commands from LLM responses."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CommandOption:
    """Represents a parsed command option."""
    command: str
    explanation: str
    confidence: float  # 0.0 to 1.0
    source: str  # "code_block", "backticks", "pattern"


class CommandParser:
    """Parser for extracting commands from LLM text responses."""

    def __init__(self):
        """Initialize the command parser."""
        # Patterns for finding commands
        self.bash_block_pattern = re.compile(
            r'```(?:bash|sh|shell)\s*\n(.*?)\n```',
            re.DOTALL | re.IGNORECASE
        )
        self.backtick_pattern = re.compile(r'`([^`]+)`')
        self.command_prefix_pattern = re.compile(
            r'(?:run|execute|try|use):\s*`?([^`\n]+)`?',
            re.IGNORECASE
        )

    def parse(self, text: str, max_options: int = 3) -> List[CommandOption]:
        """
        Parse text and extract command options.

        Args:
            text: LLM response text
            max_options: Maximum number of command options to return

        Returns:
            List of CommandOption objects, sorted by confidence
        """
        commands: List[CommandOption] = []

        # 1. Extract from bash code blocks (highest confidence)
        commands.extend(self._extract_from_code_blocks(text))

        # 2. Extract from backticks (medium confidence)
        commands.extend(self._extract_from_backticks(text))

        # 3. Extract from command prefixes (lower confidence)
        commands.extend(self._extract_from_patterns(text))

        # Remove duplicates (keep highest confidence)
        commands = self._deduplicate(commands)

        # Sort by confidence
        commands.sort(key=lambda x: x.confidence, reverse=True)

        # Filter out non-command looking strings
        commands = [cmd for cmd in commands if self._is_likely_command(cmd.command)]

        # Limit to max_options
        return commands[:max_options]

    def _extract_from_code_blocks(self, text: str) -> List[CommandOption]:
        """Extract commands from bash code blocks."""
        commands = []

        for match in self.bash_block_pattern.finditer(text):
            command_block = match.group(1).strip()

            # Try to find explanation near the code block
            explanation = self._find_explanation_near(text, match.start(), match.end())

            # Split multi-line commands
            lines = [line.strip() for line in command_block.split('\n') if line.strip()]

            # Clean lines: remove shell prompts and keep only command lines
            clean_lines = []
            for line in lines:
                # Remove common shell prompts: $, #, >, etc.
                cleaned = re.sub(r'^[\$#>]\s*', '', line)

                # Skip empty lines
                if not cleaned:
                    continue

                # Skip lines that look like output or explanations:
                # - Paths without commands (just /path/to/dir)
                # - Lines starting with numbers (ls -la output)
                # - Lines with special output patterns
                # - Lines that look like English sentences/explanations
                # - Code block language markers (bash, sh, shell, python, etc.)
                if (
                    re.match(r'^/[\w/.-]+$', cleaned) or  # Just a path
                    re.match(r'^[0-9]', cleaned) or       # Starts with number
                    re.match(r'^total\s+\d+', cleaned) or # ls output
                    re.match(r'^[drwx-]{10}', cleaned) or # ls -la permissions
                    re.match(r'^[A-Z][a-z]+.*(?:of|the|and|or|is|are|will|can)\b', cleaned) or  # English sentences
                    re.match(r'^[A-Z](?:explanation|note|example|usage|description|find|xargs|replace)\b', cleaned, re.IGNORECASE) or  # Capitalized explanation words
                    cleaned in ['bash', 'sh', 'shell', 'python', 'javascript', 'java', 'ruby', 'go', 'rust']  # Code block markers
                ):
                    continue

                # Keep lines that look like commands
                # Commands usually start with lowercase letters or special chars
                if cleaned and (cleaned[0].islower() or cleaned[0] in '~./-'):
                    clean_lines.append(cleaned)

            if not clean_lines:
                continue

            # If it's a single command, use it
            if len(clean_lines) == 1:
                commands.append(CommandOption(
                    command=clean_lines[0],
                    explanation=explanation or "Command from code block",
                    confidence=0.9,
                    source="code_block"
                ))
            # If multiple lines, treat as a script (keep together)
            elif len(clean_lines) > 1 and len(clean_lines) <= 5:
                # Keep as multi-line command
                commands.append(CommandOption(
                    command='\n'.join(clean_lines),
                    explanation=explanation or "Multi-line command",
                    confidence=0.85,
                    source="code_block"
                ))

        return commands

    def _extract_from_backticks(self, text: str) -> List[CommandOption]:
        """Extract commands from backtick-wrapped text."""
        commands = []

        for match in self.backtick_pattern.finditer(text):
            command = match.group(1).strip()

            # Skip if it's inside a code block (already extracted)
            if self._is_inside_code_block(text, match.start()):
                continue

            # Skip if it looks like inline code (not a command)
            if not self._looks_like_command(command):
                continue

            # Find explanation
            explanation = self._find_explanation_near(text, match.start(), match.end())

            commands.append(CommandOption(
                command=command,
                explanation=explanation or "Suggested command",
                confidence=0.7,
                source="backticks"
            ))

        return commands

    def _extract_from_patterns(self, text: str) -> List[CommandOption]:
        """Extract commands from command prefixes like 'Run:', 'Execute:'."""
        commands = []

        for match in self.command_prefix_pattern.finditer(text):
            command = match.group(1).strip()

            # Find explanation
            explanation = self._find_explanation_near(text, match.start(), match.end())

            commands.append(CommandOption(
                command=command,
                explanation=explanation or "Suggested command",
                confidence=0.6,
                source="pattern"
            ))

        return commands

    def _find_explanation_near(self, text: str, start: int, end: int, window: int = 150) -> Optional[str]:
        """Find explanation text near a command."""
        # Look before and after the command
        before_start = max(0, start - window)
        after_end = min(len(text), end + window)

        # Get context
        context = text[before_start:start] + " " + text[end:after_end]

        # Look for explanation patterns
        explanation_patterns = [
            r'[-→•]\s*([^.\n]+)',  # Bullet points
            r':\s*([^.\n]+)',       # After colon
            r'//\s*([^\n]+)',       # Comments
            r'#\s*([^\n]+)',        # Hash comments
        ]

        for pattern in explanation_patterns:
            match = re.search(pattern, context)
            if match:
                explanation = match.group(1).strip()
                if len(explanation) > 10:  # Avoid too short explanations
                    return explanation

        return None

    def _is_inside_code_block(self, text: str, position: int) -> bool:
        """Check if position is inside a code block."""
        # Count code block markers before this position
        before_text = text[:position]
        block_starts = len(re.findall(r'```', before_text))

        # Odd number means we're inside a block
        return block_starts % 2 == 1

    def _looks_like_command(self, text: str) -> bool:
        """Check if text looks like a shell command (not just inline code)."""
        # Commands usually start with common utilities
        common_commands = [
            'ls', 'cd', 'pwd', 'cat', 'grep', 'find', 'sed', 'awk',
            'git', 'docker', 'kubectl', 'npm', 'pip', 'python',
            'echo', 'mkdir', 'rm', 'mv', 'cp', 'chmod', 'chown',
            'sudo', 'apt', 'yum', 'brew', 'curl', 'wget', 'ssh',
            'ps', 'kill', 'top', 'df', 'du', 'tar', 'gzip'
        ]

        # Check if starts with a common command
        first_word = text.split()[0] if text.split() else ""

        # Remove sudo if present
        if first_word == 'sudo' and len(text.split()) > 1:
            first_word = text.split()[1]

        return first_word in common_commands or '|' in text or '>' in text

    def _is_likely_command(self, command: str) -> bool:
        """Filter out strings that don't look like commands."""
        # Too short
        if len(command) < 2:
            return False

        # Too long (probably not a single command)
        if len(command) > 500:
            return False

        # Contains only letters - ONLY reject if it's long (probably text, not a command)
        # Short all-letter commands like pwd, ls, cd, etc. are valid!
        if command.isalpha() and len(command) > 10:
            return False

        # Looks like a sentence (ends with period, multiple spaces)
        if command.endswith('.') and ' ' in command:
            return False

        return True

    def _deduplicate(self, commands: List[CommandOption]) -> List[CommandOption]:
        """Remove duplicate commands, keeping highest confidence."""
        seen = {}

        for cmd in commands:
            # Normalize command for comparison
            normalized = cmd.command.strip().lower()

            if normalized not in seen or cmd.confidence > seen[normalized].confidence:
                seen[normalized] = cmd

        return list(seen.values())


def format_command_menu(commands: List[CommandOption]) -> str:
    """
    Format command options as a numbered menu.

    Args:
        commands: List of CommandOption objects

    Returns:
        Formatted menu string
    """
    if not commands:
        return ""

    menu_lines = ["\n[bold cyan]📋 Suggested Commands:[/bold cyan]\n"]

    for idx, cmd in enumerate(commands, 1):
        # Truncate long commands
        display_cmd = cmd.command if len(cmd.command) <= 80 else cmd.command[:77] + "..."

        menu_lines.append(f"[bold]{idx}.[/bold] [cyan]{display_cmd}[/cyan]")
        menu_lines.append(f"   [dim]→ {cmd.explanation}[/dim]\n")

    # Always add "do nothing" option
    menu_lines.append(f"[bold]0.[/bold] [yellow]Do nothing[/yellow]")
    menu_lines.append(f"   [dim]→ Skip execution[/dim]")

    return "\n".join(menu_lines)
