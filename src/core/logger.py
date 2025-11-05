"""Centralized logging configuration for the FastAPI Agent."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.DEBUG,
    console_level: int = logging.WARNING,  # Changed from INFO to WARNING
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup and configure a logger with file and console handlers.

    Args:
        name: Logger name (usually __name__)
        log_file: Path to log file. If None, uses default 'logs/fastapi-agent.log'
        level: Logging level for file handler
        console_level: Logging level for console handler
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create logs directory if it doesn't exist
    if log_file is None:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = str(log_dir / "fastapi-agent.log")
    else:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    # Format for log messages
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # File handler - detailed logs with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Console handler - less verbose
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the standard configuration.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # If not configured yet, set it up
    if not logger.handlers:
        return setup_logger(name)

    return logger


def log_llm_request(logger: logging.Logger, model: str, messages: list, **kwargs):
    """
    Log an LLM request with formatted details.

    Args:
        logger: Logger instance
        model: Model name
        messages: List of message dicts
        **kwargs: Additional parameters (temperature, max_tokens, etc.)
    """
    logger.info(f"LLM Request to model: {model}")
    logger.debug(f"Request parameters: {kwargs}")

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Truncate long content for logging
        if len(content) > 500:
            content_preview = content[:500] + "... [truncated]"
        else:
            content_preview = content

        logger.debug(f"Message {i} [{role}]: {content_preview}")


def log_llm_response(logger: logging.Logger, response: str, success: bool = True):
    """
    Log an LLM response.

    Args:
        logger: Logger instance
        response: Response text
        success: Whether the request was successful
    """
    if success:
        logger.info("LLM Response received successfully")

        # Truncate long responses for logging
        if len(response) > 500:
            response_preview = response[:500] + "... [truncated]"
        else:
            response_preview = response

        logger.debug(f"Response content: {response_preview}")
    else:
        logger.error(f"LLM Request failed: {response}")


def log_llm_stream_chunk(logger: logging.Logger, chunk: str):
    """
    Log a streaming chunk from LLM (at debug level to avoid spam).

    Args:
        logger: Logger instance
        chunk: Response chunk
    """
    logger.debug(f"Stream chunk: {chunk[:100]}")


def log_command_execution(logger: logging.Logger, command: str, result: str, success: bool):
    """
    Log shell command execution.

    Args:
        logger: Logger instance
        command: Command that was executed
        result: Command output/result
        success: Whether command succeeded
    """
    if success:
        logger.info(f"Command executed successfully: {command}")
        logger.debug(f"Command output: {result[:500]}")
    else:
        logger.error(f"Command failed: {command}")
        logger.error(f"Error output: {result}")


def set_log_level(logger_name: Optional[str] = None, level: int = logging.DEBUG):
    """
    Change log level for a specific logger or root logger.

    Args:
        logger_name: Name of logger (None for root logger)
        level: New logging level
    """
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()

    logger.setLevel(level)

    # Also update handlers
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.setLevel(level)
