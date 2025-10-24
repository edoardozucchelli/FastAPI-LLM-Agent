# FastAPI Agent

An intelligent terminal agent with LLM integration, featuring expert modes, smart command execution, and a REST API.

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0--beta-orange.svg)](docs/CHANGELOG.md)

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
poetry install

# 2. Configure your LLM server in config.yaml

# 3. Run the CLI
./run_cli.sh
```

**That's it!** The CLI will guide you through selecting server, model, and expert mode.

---

## ✨ Features

### 🧠 Interactive CLI

- **Expert Modes**: Specialized AI assistants for Linux, Python, DevOps, Database, or General tasks
- **Response Modes**: Switch between Quick (concise) and Full (detailed) responses
- **Smart Commands**: Automatically extract and execute shell commands (Linux mode)
- **File Ingestion**: Load file contents with `@filename` syntax
- **Multi-line Input**: Dedicated `!multiline` mode or quick triple-quote syntax
- **Direct Shell**: Execute commands directly with `!ls`, `!pwd`, `!git status`
- **Keyboard Shortcuts**: Ctrl+C to interrupt, Ctrl+D to exit

### 🌐 REST API

- FastAPI server with `/chat` endpoint
- OpenAPI documentation at `/docs`
- Multiple LLM server support
- Configurable via `config.yaml`

---

## 📦 Installation

### Prerequisites

- Python 3.9+
- [Poetry](https://python-poetry.org/) (`pip install poetry`)
- [Ollama](https://ollama.ai/) or [LM Studio](https://lmstudio.ai/) running locally

### Install

```bash
# Clone the repository
git clone https://github.com/yourusername/fastapi-agent.git
cd fastapi-agent

# Install dependencies
poetry install

# Configure LLM server
cp .env.example .env
# Edit config.yaml with your LLM server details
```

---

## ⚙️ Configuration

Edit `config.yaml`:

```yaml
servers:
  - name: "Ollama Local"
    url: "http://localhost:11434"
    models:
      - "llama3.1:8b"
      - "mistral:7b"
      - "codellama"

generation:
  temperature: 0.7
  max_tokens: 2000
```

**Recommended Models:**
- **Linux/DevOps**: `llama3.1:8b`, `codellama`
- **Python/Coding**: `codellama`, `deepseek-coder`
- **General**: `llama3.1:8b`, `mistral:7b`

---

## 🎯 Usage

### Starting the CLI

```bash
./run_cli.sh
```

You'll be guided through:
1. **Server Selection**: Choose your LLM server and model
2. **Expert Mode**: Select your AI specialist (Linux/Python/DevOps/Database/General)
3. **Response Mode**: Choose Quick (concise) or Full (detailed)

### CLI Examples

#### Basic Conversation
```
You > how to list all Python files?

Agent: Use the `ls` command with a wildcard...

📋 Suggested Commands:
1. ls *.py
   → List Python files in current directory

2. find . -name "*.py"
   → Find Python files recursively

0. Skip

Select [0]: 1
[Command executes...]
```

#### Switch Expert Modes
```
You > !expert python
✓ Expert mode: 🐍 Python
💡 Conversation history cleared

You > write a function to sort a list
Agent: Here's a Python solution...
```

#### Load Files
```
You > review this code @src/main.py

Agent: [analyzes the file contents]
```

#### Multi-line Input
```
You > !multiline
📝 Multi-line input mode
Type or paste your text. Press Ctrl+D (Unix) or Ctrl+Z (Windows) on a new line to finish.
... def calculate_sum(a, b):
...     """Calculate the sum of two numbers."""
...     return a + b
... [Ctrl+D]
✓ Captured 3 lines (89 characters)

Agent: [analyzes your code]
```

#### Direct Shell Commands
```
You > !git status
On branch main...

You > !ls -la
total 48
drwxr-xr-x  6 user  staff   192 Oct 24 15:00 .
...
```

### CLI Special Commands

| Command | Description |
|---------|-------------|
| `!quit`, `!exit`, `!q` | Exit the CLI |
| `!expert <mode>` | Switch expert: `linux`, `python`, `devops`, `database`, `general` |
| `!mode <type>` | Switch response: `quick` or `full` |
| `!status` | Show current configuration |
| `!clear` | Clear conversation history |
| `!multiline` | Enter dedicated multi-line input mode |
| `!help` | Show help message |
| `!<command>` | Execute any shell command directly |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` (during response) | Interrupt LLM streaming |
| `Ctrl+C` (at prompt) | Show exit reminder |
| `Ctrl+D` (at prompt) | Exit CLI |
| `Ctrl+D` (in multiline) | Finish and send multi-line input |
| `Enter` (empty) | Skip / Continue |

---

## 🌐 Running the API

```bash
# Start the API server
./run_api.sh

# Or with uvicorn directly
uvicorn src.api.main:app --reload --port 8000
```

Access the API:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

```bash
# Chat completion
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "model": "llama3.1:8b"}'

# Streaming chat
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a story"}'
```

---

## 📁 Project Structure

```
fastapi-agent/
├── src/
│   ├── core/              # Shared: LLM client, config, tools
│   ├── api/               # REST API with FastAPI
│   └── cli/               # Interactive terminal
├── tests/                 # Tests organized by component
│   ├── core/
│   ├── api/
│   └── cli/
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md
│   ├── PROJECT_STRUCTURE.md
│   └── CHANGELOG.md
├── config.yaml           # LLM server configuration
├── pyproject.toml        # Dependencies
├── run_cli.sh            # CLI runner
└── run_api.sh            # API runner
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Test specific components
pytest tests/core/
pytest tests/cli/
pytest tests/api/

# With coverage
pytest --cov=src tests/

# Verbose output
pytest -v
```

---

## 🛠️ Development

```bash
# Install dev dependencies
poetry install

# Run CLI in dev mode
python -m src.cli.interactive_terminal

# Run API in dev mode
uvicorn src.api.main:app --reload

# Format code
black src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/
```

---

## 🧠 Expert Modes Explained

### 🐧 Linux Expert
- **Focus**: Shell commands, bash scripting, system administration
- **Use for**: File operations, process management, system configuration
- **Temperature**: 0.4 (more deterministic)

### 🐍 Python Expert
- **Focus**: Python code, libraries, best practices
- **Use for**: Writing functions, debugging, code optimization
- **Temperature**: 0.5 (balanced)

### 🚀 DevOps Expert
- **Focus**: Docker, Kubernetes, CI/CD, infrastructure
- **Use for**: Container management, deployment, automation
- **Temperature**: 0.4 (deterministic)

### 🗄️ Database Expert
- **Focus**: SQL queries, schema design, optimization
- **Use for**: Database operations, query writing, performance tuning
- **Temperature**: 0.4 (precise)

### 💬 General Assistant
- **Focus**: Mixed capabilities, adaptive
- **Use for**: General questions, varied tasks
- **Temperature**: 0.7 (creative)

---

## 📖 Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - Technical design and components
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Directory organization details
- **[Changelog](docs/CHANGELOG.md)** - Version history and updates

---

## 🔧 Troubleshooting

### CLI won't start
- Check that Poetry installed dependencies: `poetry install`
- Verify Python version: `python --version` (need 3.9+)
- Check LLM server is running: `curl http://localhost:11434`

### Commands not executing
- Command suggestions only work in **Linux Expert mode**
- Check command parser with `!status`
- Ensure you're not in Python/Database mode

### Ctrl+C not working
- Press Ctrl+C during streaming to interrupt
- At the prompt, use `!quit` to exit
- Try Ctrl+D as alternative

### API errors
- Check `config.yaml` has correct server URL
- Verify LLM server is accessible
- Check API logs for details

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📊 Version

**v0.1.0-beta** - See [CHANGELOG](docs/CHANGELOG.md) for details

### What's New in Beta
- ✨ Expert mode system (5 specialized modes)
- ⚡ Response mode switching (Quick/Full)
- 📋 Smart command parsing and execution
- 🎯 Improved system prompts
- 🔧 Direct shell command execution
- ⌨️ Better keyboard shortcuts (Ctrl+C, Ctrl+D)

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Terminal UI with [Rich](https://rich.readthedocs.io/)
- Input handling with [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/)
- Powered by [Ollama](https://ollama.ai/) / [LM Studio](https://lmstudio.ai/)

---

## 💡 Tips

- Start with **Linux Expert** for system tasks
- Use **Python Expert** for coding questions
- Switch modes with `!expert <mode>` anytime
- Use `!multiline` for pasting code or long text (finish with Ctrl+D)
- Use `@filename` to load file contents into conversation
- Press Ctrl+C during long responses to interrupt
- Use `!clear` to reset conversation context

---

**Happy coding!** 🚀
