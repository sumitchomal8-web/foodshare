"""
tests/conftest.py
Shared pytest configuration.

Fix for Python 3.14 / Windows: use SelectorEventLoop (not ProactorEventLoop).
The ProactorEventLoop deadlocks when anyio+Starlette's TestClient runs async
code from pytest's sync thread context.
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
