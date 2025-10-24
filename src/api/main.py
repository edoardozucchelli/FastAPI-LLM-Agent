"""FastAPI application for the agent."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from src.core.llm_client import LLMClient
from src.core.config import config


# Use first server from config as default
default_server = config.servers[0]
llm_client = LLMClient(
    base_url=default_server.url,
    model=default_server.models[0],
    use_instruct=True
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: nothing to do here
    yield
    # Shutdown: cleanup
    await llm_client.close()


app = FastAPI(title="FastAPI Agent", version="0.1.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    model: str = default_server.models[0]
    temperature: float = config.generation.temperature
    max_tokens: int = config.generation.max_tokens


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "FastAPI Agent is running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint."""
    messages = [{"role": "user", "content": request.message}]

    response = await llm_client.chat(
        messages=messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    return ChatResponse(response=response)
