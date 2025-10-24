# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0-beta] - 2025-10-24

### 🎉 Initial BETA Release

#### ✨ New Features

**Agent CLI (Interactive Terminal)**
- 🐧 **Expert Mode System**: 5 specialized modes (Linux, Python, DevOps, Database, General)
- ⚡ **Response Modes**: Quick (concise) and Full (detailed) modes
- 📋 **Command Suggestions**: Smart command parsing and execution menu (Linux mode only)
- 📂 **File Ingestion**: Load file contents with `@filename` syntax
- 💬 **Multi-line Input**: Support for triple quotes and backticks
- 🔄 **Direct Shell Commands**: Execute commands with `!ls`, `!pwd`, etc.
- 🎯 **Conversation Management**: Clear history, switch modes, view status

#### 🛠️ Improvements

**Command Parser**
- Intelligent command extraction from LLM responses
- Filters shell prompts (`$`, `#`, `>`)
- Removes command output and explanation text
- Supports multi-line commands
- Confidence scoring for suggestions

**User Experience**
- Concise system prompts (~400 chars, down from ~1600)
- Better LLM instruction following
- Cleaner response formatting
- Improved error handling

#### ⌨️ Keyboard Shortcuts

- `Ctrl+C` during response → Interrupt LLM streaming
- `Ctrl+C` at prompt → Show exit reminder
- `Ctrl+D` → Exit CLI gracefully

#### 🎨 Special Commands

- `!quit`, `!exit`, `!q` → Exit
- `!expert <mode>` → Switch expert mode (clears history)
- `!mode quick|full` → Switch response mode
- `!status` → Show configuration
- `!clear` → Clear conversation history
- `!help` → Show help
- `!<command>` → Execute shell command directly

#### 📁 Project Structure

```
fastapi-agent/
├── agent/              # Core LLM client and tools
├── agent-cli/          # Interactive CLI application
├── tests/             # Test suites
└── docs/              # Documentation
```

#### 🧹 Cleanup

- Removed temporary test files
- Removed backup files (`.backup`, `.old`)
- Updated `.gitignore` for cleaner repository

### 🐛 Known Issues

- Command suggestions only work in Linux Expert mode (by design)
- Some LLM models may not follow system prompts perfectly (use better models like llama3.1:8b+)

### 📝 Notes

This is a BETA release. The API and CLI are functional but may have minor bugs.
Feedback and contributions are welcome!

### 🔗 Links

- [Getting Started Guide](GETTING_STARTED.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [Project Structure](PROJECT_STRUCTURE.md)
