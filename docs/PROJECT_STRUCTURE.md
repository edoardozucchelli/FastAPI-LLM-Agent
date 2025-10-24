# Project Structure

## Directory Structure

```
fastapi-agent/
├── src/
│   ├── core/              # Shared components
│   ├── api/               # REST API
│   └── cli/               # Interactive CLI
├── tests/                 # Tests by component
├── config.yaml           # Configuration
├── run_cli.sh            # CLI runner
└── run_api.sh            # API runner
```

## Components

### Core (`src/core/`)
- `llm_client.py` - LLM HTTP client
- `config.py` - Configuration management
- `tools.py` - Tool definitions

### API (`src/api/`)
- `main.py` - FastAPI application

### CLI (`src/cli/`)
- `interactive_terminal.py` - Main CLI
- `expert_modes.py` - Expert system
- `command_parser.py` - Command extraction
- Other CLI utilities

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.
