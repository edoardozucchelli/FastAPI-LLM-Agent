"""Configuration for the agent."""

import yaml
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel


class ServerConfig(BaseModel):
    """Configuration for a single server."""
    name: str
    url: str
    models: List[str]


class GenerationConfig(BaseModel):
    """Generation parameters."""
    temperature: float = 0.7
    max_tokens: int = 2000


class ApiConfig(BaseModel):
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000


class Config(BaseModel):
    """Main configuration."""
    servers: List[ServerConfig]
    generation: GenerationConfig
    api: ApiConfig


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file."""
    path = Path(config_path)

    if not path.exists():
        # Return default configuration if file doesn't exist
        return Config(
            servers=[
                ServerConfig(
                    name="Ollama Local",
                    url="http://localhost:11434",
                    models=["mistral-7b", "llama2"]
                )
            ],
            generation=GenerationConfig(),
            api=ApiConfig()
        )

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return Config(**data)


# Load global config
config = load_config()
