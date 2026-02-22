"""
Typed event bus for the async streaming bridge.

All bridge output is expressed as frozen dataclasses posted to an asyncio.Queue.
Consumers pattern-match on the `type` literal field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union


@dataclass(frozen=True)
class AgentSpec:
    """Specification for invoking an agent subprocess."""

    name: str       # Human-readable identifier, e.g., "claude"
    command: str    # Executable name, e.g., "claude"
    args: tuple[str, ...] = ()

    def build_argv(self, prompt: str) -> list[str]:
        """Return the full argument vector: [command, *args, prompt]."""
        return [self.command, *self.args, prompt]


@dataclass(frozen=True)
class TokenChunk:
    """One streamed line of text from an agent subprocess."""

    agent: str
    text: str
    type: Literal["token"] = "token"


@dataclass(frozen=True)
class AgentDone:
    """Terminal event: agent completed successfully (exit code 0)."""

    agent: str
    full_text: str
    exit_code: int
    type: Literal["done"] = "done"


@dataclass(frozen=True)
class AgentError:
    """Terminal event: agent exited with a non-zero exit code."""

    agent: str
    message: str
    exit_code: int
    type: Literal["error"] = "error"


@dataclass(frozen=True)
class AgentTimeout:
    """Terminal event: agent exceeded the global timeout."""

    agent: str
    type: Literal["timeout"] = "timeout"


BridgeEvent = Union[TokenChunk, AgentDone, AgentError, AgentTimeout]
