# Architecture Overview

This document describes the architecture of the FastAPI Agent monorepo.

## Project Structure

```
fastapi-agent/
├── src/
│   ├── core/                   # Shared components
│   │   ├── __init__.py
│   │   ├── llm_client.py       # LLM HTTP client
│   │   ├── config.py           # Configuration loader
│   │   └── tools.py            # Tool definitions
│   │
│   ├── api/                    # REST API
│   │   ├── __init__.py
│   │   └── main.py             # FastAPI application
│   │
│   └── cli/                    # Interactive CLI
│       ├── __init__.py
│       ├── interactive_terminal.py  # Main CLI orchestrator
│       ├── expert_modes.py         # Expert system & prompts
│       ├── command_parser.py       # Command extraction
│       ├── command_executor.py     # Command execution
│       ├── input_handler.py        # Multi-line input & file ingestion
│       └── llm_client_wrapper.py   # CLI-specific LLM wrapper
│
├── tests/                      # Tests organized by component
│   ├── core/                   # Core component tests
│   ├── api/                    # API tests
│   └── cli/                    # CLI tests
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         # This file
│   ├── PROJECT_STRUCTURE.md    # Directory organization
│   └── CHANGELOG.md            # Version history
│
├── config.yaml                 # LLM server configuration
├── pyproject.toml              # Dependencies & scripts
├── run_cli.sh                  # CLI runner script
└── run_api.sh                  # API runner script
```

## Component Layers

### Layer 1: Core Library (`src/core/`)

**Purpose**: Shared components used by both API and CLI

**Components**:
- **LLMClient** (`llm_client.py`): HTTP client for communicating with Ollama/LM Studio
  - Async streaming support with `httpx.AsyncClient`
  - Stream cancellation with `aclose()` for interrupt handling
  - Compatible with OpenAI API format

- **Config** (`config.py`): YAML-based configuration system
  - Pydantic-based settings validation
  - Multiple server support
  - Per-model configuration

- **Tools** (`tools.py`): Tool/function definitions
  - OpenAI function calling format
  - Shell command execution tool

**Usage**: Imported by both API and CLI applications

### Layer 2: REST API (`src/api/`)

**Purpose**: HTTP API server for chat completions

**Components**:
- **FastAPI Application** (`main.py`)
  - `/chat` endpoint for non-streaming responses
  - `/chat/stream` endpoint for streaming responses
  - OpenAPI documentation at `/docs`
  - Lifespan management for LLM client

**API Features**:
- Multiple LLM server selection
- Model selection per request
- Streaming and non-streaming modes
- CORS support for web clients

### Layer 3: Interactive CLI (`src/cli/`)

**Purpose**: Advanced terminal interface with expert modes and command execution

**Components**:

1. **InteractiveCLI** (`interactive_terminal.py`)
   - Main orchestrator and command loop
   - Startup flow with server/model/expert selection
   - Special command handling (!quit, !expert, !mode, etc.)
   - Direct shell command execution (!ls, !pwd, etc.)
   - Keyboard interrupt handling (Ctrl+C, Ctrl+D)

2. **Expert Modes** (`expert_modes.py`)
   - 5 specialized modes: Linux, Python, DevOps, Database, General
   - Custom system prompts per expert
   - Response modes: Quick (concise) vs Full (detailed)
   - Automatic temperature adjustment per expert

3. **Command Parser** (`command_parser.py`)
   - Extracts shell commands from LLM responses
   - Filters out shell prompts ($, #) and output lines
   - Pattern-based detection with regex
   - Expert-aware (only parses in Linux mode)

4. **Command Executor** (`command_executor.py`)
   - Interactive command approval flow
   - Numbered command selection
   - Subprocess execution with output capture
   - Working directory display

5. **Input Handler** (`input_handler.py`)
   - Multi-line input support (triple quotes, backticks)
   - File reference ingestion (`@filename.txt`)
   - Async input with prompt-toolkit
   - Input history management

6. **LLM Client Wrapper** (`llm_client_wrapper.py`)
   - Wraps core `LLMClient`
   - Conversation history management
   - Expert mode integration
   - System prompt injection
   - Tool definitions support

## Data Flow

### Basic Chat Flow
```
User Input → InputHandler → LLMClientWithTools → LLM Server → Stream Response → Display
```

### Expert Mode Flow
```
User selects Expert → Load System Prompt + Temperature
                    ↓
             Update LLM Client Config
                    ↓
             All messages use expert context
```

### Command Execution Flow (Linux Mode Only)
```
User Input → LLMClientWithTools → LLM Server → Response with Commands
          ↓
CommandParser → Extract Commands → CommandExecutor
          ↓
    Show Numbered List → User Selects → Execute → Show Output
          ↓
    Result → LLMClientWithTools → Follow-up Response
```

### File Ingestion Flow
```
User: "review @src/main.py"
    ↓
InputHandler → Read file contents → Inject into message
    ↓
LLMClientWithTools → LLM sees file contents in context
```

## Configuration System

### config.yaml Structure
```yaml
servers:
  - name: "Ollama Local"
    url: "http://localhost:11434"
    models:
      - "llama3.1:8b"
      - "mistral:7b"
      - "codellama"

generation:
  temperature: 0.7  # Default, overridden by expert modes
  max_tokens: 2000
```

### Expert Mode Temperatures
- **Linux Expert**: 0.4 (deterministic, precise commands)
- **Python Expert**: 0.5 (balanced, accurate code)
- **DevOps Expert**: 0.4 (precise configurations)
- **Database Expert**: 0.4 (exact SQL queries)
- **General Assistant**: 0.7 (creative, conversational)

## Security Considerations

### Command Execution
- Commands only extracted in **Linux Expert mode**
- All commands require explicit user approval
- Commands are numbered and selectable
- Full command preview before execution
- Working directory clearly displayed
- No automatic execution without user interaction

### File Operations
- File ingestion uses standard Python file reading
- Paths are resolved relative to working directory
- File contents shown in terminal with syntax highlighting

### Interrupt Safety
- Ctrl+C properly cancels LLM streams with `aclose()`
- Async tasks cleaned up properly
- No zombie processes from interrupted commands

## Expert Mode System

### How Expert Modes Work

1. **System Prompt Injection**: Each expert has a specialized system prompt that guides the LLM's behavior
2. **Temperature Adjustment**: More deterministic temperatures for technical experts
3. **Response Mode**: Quick vs Full changes verbosity instructions
4. **Context Isolation**: Switching experts clears conversation history

### Expert Mode Use Cases

| Expert | Best For | Example Queries |
|--------|----------|-----------------|
| Linux | Shell commands, file ops, system admin | "Find all Python files", "Create backup script" |
| Python | Code writing, debugging, libraries | "Write a function to parse JSON", "Optimize this code" |
| DevOps | Docker, K8s, CI/CD, deployment | "Create Dockerfile", "Setup GitHub Actions" |
| Database | SQL queries, schema design, optimization | "Write query to join tables", "Create index" |
| General | Mixed tasks, explanations, general help | "Explain REST APIs", "Compare technologies" |

## Command Parser Details

### Pattern Recognition
The command parser uses regex patterns to identify shell commands:
- Lines starting with `$`, `#`, or `>` (shell prompts)
- Common command patterns (ls, cd, grep, etc.)
- Multi-line commands with backslash continuation

### Filtering Logic
Filters out:
- Shell prompts (`$ `, `# `)
- Output-like lines (indented, contains ":", etc.)
- Long strings of only letters (likely prose, not commands)
- Comments and explanations

### Example
```
LLM Response:
"You can list files with:
$ ls -la
total 48
-rw-r--r-- 1 user ...

Or find Python files:
find . -name "*.py"
"

Extracted Commands:
1. ls -la
2. find . -name "*.py"
```

## Development Workflow

### Running the CLI
```bash
./run_cli.sh
# or
python -m src.cli.interactive_terminal
```

### Running the API
```bash
./run_api.sh
# or
uvicorn src.api.main:app --reload --port 8000
```

### Running Tests
```bash
# All tests
pytest

# Specific component
pytest tests/core/
pytest tests/api/
pytest tests/cli/

# With coverage
pytest --cov=src tests/
```

## Extension Points

### Adding New Expert Modes
Edit `src/cli/expert_modes.py`:
```python
class ExpertMode(Enum):
    NEW_EXPERT = "new_expert"

EXPERT_PROMPTS = {
    ExpertMode.NEW_EXPERT: {
        "system_prompt": "Your expert system prompt...",
        "temperature": 0.5,
        "description": "What this expert does"
    }
}
```

### Adding New Tools
1. Define tool in `src/core/tools.py`
2. Add execution logic in CLI or API
3. Update system prompts if needed

### Custom Input Syntax
Extend `InputHandler` in `src/cli/input_handler.py`:
- Add new pattern detection
- Implement transformation logic
- Return processed message

### Alternative Frontends
The core library (`src/core/`) can be reused for:
- Web UI (using the FastAPI endpoints)
- VS Code extension
- Jupyter notebook interface
- Slack/Discord bots
- Custom applications

## Technical Stack

### Core Dependencies
- **httpx**: Async HTTP client for LLM servers
- **pydantic**: Configuration validation and settings
- **pyyaml**: Configuration file parsing

### API Dependencies
- **FastAPI**: Modern web framework
- **uvicorn**: ASGI server

### CLI Dependencies
- **Rich**: Terminal formatting and output
- **prompt-toolkit**: Advanced async input handling

### Development Dependencies
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities

## Future Enhancements

### Planned Features
- [ ] Native function calling support when local LLMs support it
- [ ] Conversation saving/loading
- [ ] Command history export
- [ ] Configurable keyboard shortcuts
- [ ] Plugin system for custom experts
- [ ] Web UI frontend
- [ ] Docker deployment configuration

### Possible Improvements
- [ ] Sandbox mode for safer command execution
- [ ] Command whitelist/blacklist per expert
- [ ] Multi-turn tool execution
- [ ] Streaming command output
- [ ] Background task execution
- [ ] Session persistence across restarts
