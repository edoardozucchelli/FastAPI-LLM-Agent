"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set the event loop policy for async tests."""
    import asyncio
    return asyncio.get_event_loop_policy()
