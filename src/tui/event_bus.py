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
    system_prompt: str = ""
    # If set, system_prompt is passed as --flag "text" before the user prompt.
    # If empty, system_prompt is prepended directly to the user prompt string.
    system_prompt_flag: str = ""

    def build_argv(self, prompt: str) -> list[str]:
        """Return the full argument vector, injecting system_prompt if set."""
        argv = [self.command, *self.args]
        if self.system_prompt:
            if self.system_prompt_flag:
                argv.extend([self.system_prompt_flag, self.system_prompt])
            else:
                prompt = f"{self.system_prompt}\n\n---\n\n{prompt}"
        argv.append(prompt)
        return argv


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
