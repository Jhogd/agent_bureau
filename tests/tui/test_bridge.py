"""
Phase 1, Plan 02: Async streaming bridge tests.

Uses FakeAgentRunner — no real subprocess, no real CLI tool required.
pytest-asyncio asyncio_mode=auto configured in pyproject.toml — no decorator needed.
"""

import asyncio
import pytest

from tui.event_bus import (
    AgentSpec,
    TokenChunk,
    AgentDone,
    AgentError,
    AgentTimeout,
    BridgeEvent,
)


# ---------------------------------------------------------------------------
# FakeAgentRunner: drop-in for real subprocess runner
# ---------------------------------------------------------------------------


class FakeAgentRunner:
    """Async generator fake — streams lines with optional delay and failure."""

    def __init__(
        self,
        name: str,
        lines: list[str],
        exit_code: int = 0,
        delay: float = 0.0,
    ) -> None:
        self.name = name
        self.lines = lines
        self.exit_code = exit_code
        self.delay = delay

    async def stream_lines(self, prompt: str):
        for line in self.lines:
            if self.delay:
                await asyncio.sleep(self.delay)
            yield line
        if self.exit_code != 0:
            raise RuntimeError(f"{self.name} exited with code {self.exit_code}")


# ---------------------------------------------------------------------------
# run_bridge_with_fakes: bridge consumer driven by FakeAgentRunner
# ---------------------------------------------------------------------------


async def run_bridge_with_fakes(
    prompt: str,
    runner_a: FakeAgentRunner,
    runner_b: FakeAgentRunner,
    timeout: float = 30.0,
) -> list[BridgeEvent]:
    """Bridge implementation that accepts fake runners — testable without subprocesses."""
    q: asyncio.Queue[BridgeEvent] = asyncio.Queue()

    async def _run(runner: FakeAgentRunner) -> None:
        collected: list[str] = []
        try:
            async def _stream():
                async for line in runner.stream_lines(prompt):
                    collected.append(line)
                    await q.put(TokenChunk(agent=runner.name, text=line))

            await asyncio.wait_for(_stream(), timeout=timeout)
            await q.put(
                AgentDone(agent=runner.name, full_text="\n".join(collected), exit_code=0)
            )
        except asyncio.TimeoutError:
            await q.put(AgentTimeout(agent=runner.name))
        except RuntimeError as exc:
            await q.put(AgentError(agent=runner.name, message=str(exc), exit_code=1))

    task_a = asyncio.create_task(_run(runner_a))
    task_b = asyncio.create_task(_run(runner_b))

    events: list[BridgeEvent] = []
    done_count = 0
    while done_count < 2:
        event = await q.get()
        events.append(event)
        if event.type in ("done", "error", "timeout"):
            done_count += 1

    await asyncio.gather(task_a, task_b)
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_both_agents_produce_tokens():
    """Both agents stream token events when both succeed."""
    # Arrange
    runner_a = FakeAgentRunner("claude", ["Line A1", "Line A2"])
    runner_b = FakeAgentRunner("codex", ["Line B1"])

    # Act
    events = await run_bridge_with_fakes("test prompt", runner_a, runner_b)

    # Assert
    token_agents = {e.agent for e in events if e.type == "token"}
    assert "claude" in token_agents
    assert "codex" in token_agents


async def test_error_does_not_kill_surviving_agent():
    """AGENT-04: When one agent errors, the other completes normally."""
    # Arrange — codex errors quickly, claude takes slightly longer
    runner_a = FakeAgentRunner("claude", ["A1", "A2"], exit_code=0, delay=0.05)
    runner_b = FakeAgentRunner("codex", ["B1"], exit_code=1, delay=0.01)

    # Act
    events = await run_bridge_with_fakes("test prompt", runner_a, runner_b)

    # Assert
    error_events = [e for e in events if e.type == "error"]
    done_events = [e for e in events if e.type == "done"]
    assert any(e.agent == "codex" for e in error_events)
    assert any(e.agent == "claude" for e in done_events)


async def test_timeout_does_not_kill_surviving_agent():
    """AGENT-03: When one agent times out, the other completes normally."""
    # Arrange — claude hangs forever, codex is fast
    runner_a = FakeAgentRunner("claude", ["A1"], delay=9999.0)  # Will hang
    runner_b = FakeAgentRunner("codex", ["B1"], delay=0.01)

    # Act
    events = await run_bridge_with_fakes("test prompt", runner_a, runner_b, timeout=0.1)

    # Assert
    timeout_events = [e for e in events if e.type == "timeout"]
    done_events = [e for e in events if e.type == "done"]
    assert any(e.agent == "claude" for e in timeout_events)
    assert any(e.agent == "codex" for e in done_events)


async def test_terminal_events_exactly_two():
    """Bridge always emits exactly 2 terminal events (done/error/timeout), one per agent."""
    # Arrange
    runner_a = FakeAgentRunner("claude", ["A1"])
    runner_b = FakeAgentRunner("codex", ["B1"])

    # Act
    events = await run_bridge_with_fakes("prompt", runner_a, runner_b)

    # Assert
    terminal = [e for e in events if e.type in ("done", "error", "timeout")]
    assert len(terminal) == 2


async def test_done_event_contains_full_text():
    """AgentDone.full_text contains the complete accumulated text from all TokenChunk events."""
    # Arrange
    runner = FakeAgentRunner("claude", ["Line 1", "Line 2", "Line 3"])
    runner_b = FakeAgentRunner("codex", [])

    # Act
    events = await run_bridge_with_fakes("prompt", runner, runner_b)

    # Assert
    done = next(e for e in events if e.type == "done" and e.agent == "claude")
    assert "Line 1" in done.full_text
    assert "Line 2" in done.full_text
    assert "Line 3" in done.full_text


async def test_agent_spec_build_argv():
    """AgentSpec.build_argv builds correct argument vector."""
    # Arrange
    spec = AgentSpec(name="claude", command="claude")
    spec_with_args = AgentSpec(name="codex", command="codex", args=("--model", "o4-mini"))

    # Act / Assert
    assert spec.build_argv("hello world") == ["claude", "hello world"]
    assert spec_with_args.build_argv("fix bug") == [
        "codex", "--model", "o4-mini", "fix bug"
    ]


async def test_both_error_still_two_terminal_events():
    """Both agents failing still produces exactly 2 terminal events."""
    # Arrange
    runner_a = FakeAgentRunner("claude", ["A1"], exit_code=1)
    runner_b = FakeAgentRunner("codex", ["B1"], exit_code=2)

    # Act
    events = await run_bridge_with_fakes("prompt", runner_a, runner_b)

    # Assert
    terminal = [e for e in events if e.type in ("done", "error", "timeout")]
    assert len(terminal) == 2
    assert all(e.type == "error" for e in terminal)
