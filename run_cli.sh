#!/bin/bash
# FastAPI Agent - CLI Runner

# Make sure we're in the project root
cd "$(dirname "$0")"

# Run the interactive CLI
python3 -m src.cli.interactive_terminal "$@"
