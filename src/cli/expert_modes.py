"""Expert mode definitions with specialized system prompts."""

from typing import Dict, Any
from enum import Enum


class ExpertMode(str, Enum):
    """Available expert modes."""
    LINUX = "linux"
    PYTHON = "python"
    DEVOPS = "devops"
    DATABASE = "database"
    GENERAL = "general"


class ResponseMode(str, Enum):
    """Response detail modes."""
    QUICK = "quick"
    FULL = "full"


# Expert mode configurations
EXPERT_CONFIGS: Dict[ExpertMode, Dict[str, Any]] = {
    ExpertMode.LINUX: {
        "name": "🐧 Linux Expert",
        "description": "Shell, scripting, system administration",
        "icon": "🐧",
        "temperature": 0.4,  # More deterministic for commands
        "max_tokens_quick": 400,
        "max_tokens_full": 1500,
    },
    ExpertMode.PYTHON: {
        "name": "🐍 Python Expert",
        "description": "Coding, debugging, best practices",
        "icon": "🐍",
        "temperature": 0.5,
        "max_tokens_quick": 500,
        "max_tokens_full": 2000,
    },
    ExpertMode.DEVOPS: {
        "name": "🚀 DevOps Expert",
        "description": "Docker, K8s, CI/CD, deployment",
        "icon": "🚀",
        "temperature": 0.4,
        "max_tokens_quick": 400,
        "max_tokens_full": 1500,
    },
    ExpertMode.DATABASE: {
        "name": "🗄️  Database Expert",
        "description": "SQL, optimization, design",
        "icon": "🗄️",
        "temperature": 0.4,
        "max_tokens_quick": 400,
        "max_tokens_full": 1500,
    },
    ExpertMode.GENERAL: {
        "name": "💬 General Assistant",
        "description": "Mixed capabilities",
        "icon": "💬",
        "temperature": 0.7,
        "max_tokens_quick": 500,
        "max_tokens_full": 2000,
    },
}


def get_system_prompt(expert_mode: ExpertMode, response_mode: ResponseMode) -> str:
    """
    Generate system prompt based on expert and response mode.

    Args:
        expert_mode: The expert specialization
        response_mode: Quick or full response mode

    Returns:
        System prompt string
    """
    # Response mode instructions - CONCISE!
    response_instruction = ""
    if response_mode == ResponseMode.QUICK:
        response_instruction = "STYLE: Quick and concise. Get to the point. No long explanations."
    else:  # FULL
        response_instruction = "STYLE: Detailed with examples and context when helpful."

    # Base instructions for all modes - KEEP IT SHORT!
    base_instructions = """
When suggesting commands:
- Wrap in backticks: `command`
- Use code blocks for multi-line
- Brief explanation only
- Mention risks if critical
"""

    # Expert-specific prompts
    expert_prompts = {
        ExpertMode.LINUX: """
Linux system expert. Answer with Linux/bash commands ONLY.
NO Python/Java/PowerShell unless asked.
Focus: shell scripting, system utilities, file operations.
""",

        ExpertMode.PYTHON: """
Python expert. Answer with Python code ONLY.
NO bash/shell unless needed.
Focus: Python 3.x, clean code, best practices.
""",

        ExpertMode.DEVOPS: """
DevOps expert. Focus on Docker, K8s, CI/CD, infrastructure.
Prefer containers and automation over app code.
""",

        ExpertMode.DATABASE: """
Database expert. Provide SQL queries and DB solutions.
Focus: queries, schema, optimization, indexes.
""",

        ExpertMode.GENERAL: """
General AI assistant. Adapt to questions.
Provide clear, accurate info.
"""
    }

    # Expert-specific reminders (to reinforce the role)
    expert_reminders = {
        ExpertMode.LINUX: "⚠️ LINUX MODE: Use bash/shell commands only.",
        ExpertMode.PYTHON: "⚠️ PYTHON MODE: Use Python code only.",
        ExpertMode.DEVOPS: "⚠️ DEVOPS MODE: Focus on containers & infrastructure.",
        ExpertMode.DATABASE: "⚠️ DATABASE MODE: Use SQL queries.",
        ExpertMode.GENERAL: "GENERAL MODE: Adapt to context."
    }

    # Combine all parts - MUCH SHORTER NOW!
    system_prompt = f"""{expert_prompts[expert_mode]}
{response_instruction}
{base_instructions}
{expert_reminders[expert_mode]}
""".strip()

    return system_prompt


def get_expert_display_info() -> list[tuple[int, str, str]]:
    """
    Get expert modes for display in selection menu.

    Returns:
        List of (index, icon+name, description) tuples
    """
    return [
        (i + 1, config["name"], config["description"])
        for i, (mode, config) in enumerate(EXPERT_CONFIGS.items())
    ]


def get_response_mode_display_info() -> list[tuple[int, str, str]]:
    """
    Get response modes for display in selection menu.

    Returns:
        List of (index, name, description) tuples
    """
    return [
        (1, "⚡ Quick", "Concise answers (faster)"),
        (2, "📖 Full", "Detailed explanations (complete)")
    ]


def get_expert_config(expert_mode: ExpertMode, response_mode: ResponseMode) -> Dict[str, Any]:
    """
    Get configuration for given expert and response mode.

    Returns:
        Dictionary with temperature and max_tokens
    """
    config = EXPERT_CONFIGS[expert_mode]

    max_tokens_key = "max_tokens_quick" if response_mode == ResponseMode.QUICK else "max_tokens_full"

    return {
        "temperature": config["temperature"],
        "max_tokens": config[max_tokens_key],
        "name": config["name"],
        "icon": config["icon"]
    }
