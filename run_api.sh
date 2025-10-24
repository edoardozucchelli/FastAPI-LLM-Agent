#!/bin/bash
# FastAPI Agent - API Server Runner

# Make sure we're in the project root
cd "$(dirname "$0")"

# Run the FastAPI server with uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
