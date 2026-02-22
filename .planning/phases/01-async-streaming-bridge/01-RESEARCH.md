# Phase 1: Async Streaming Bridge - Research

**Researched:** 2026-02-21
**Domain:** asyncio subprocess streaming, PTY, typed event queues, Python testing
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Streaming granularity**
- Use PTY (pseudo-terminal) to give each agent subprocess a fake terminal, so agents stream output exactly as they would in a real terminal (no buffering)
- Try PTY first; if PTY fails (e.g., in certain CI environments), fall back to piped mode with a warning — do not crash
- Preserve ANSI color codes from agent output; do not strip them. The TUI should render agent colors.
- Streaming chunk granularity: Claude's Discretion — pick whatever feels most natural in the pane (every raw chunk or complete lines)

**Error containment**
- If one agent crashes or times out, the other agent's stream continues uninterrupted
- The failed agent's pane shows a clear error; the surviving agent finishes normally
- After one agent fails and the other finishes, user has both options: apply the surviving agent's answer as normal, OR retry the failed agent only
- Single global timeout applies to all agents (not per-agent config)

**Agent invocation**
- Invoke agents with raw text output — no JSON wrapping, no `--output-format json`
- Invoke as a command-line argument: `claude "prompt"`, `codex "prompt"`, etc.
- The old disagree_v1 batch CLI and JSON schema are dropped — not maintained alongside the TUI
- How command templates are structured for the bridge (config vs hardcoded): Claude's Discretion — pick whatever makes Phase 1 testable and Phase 5 (agent discovery/config) easy to extend

**Concurrency model**
- Exactly 2 agents — not generalized to N
- Both agents run in parallel from the moment the prompt is submitted
- Bridge waits for BOTH agents to finish streaming before running disagreement classification
- Classification happens once, on complete responses

### Claude's Discretion

- Streaming chunk granularity: every raw chunk or complete lines
- Command template structure: config vs hardcoded

### Deferred Ideas (OUT OF SCOPE)

- N-agent support (3+ agents) — considered and explicitly deferred; 2 agents is the v1 design
- Per-agent timeout configuration — deferred to config phase; single global timeout for v1
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGENT-03 | If an agent times out, user sees a clear error message and the session recovers gracefully | Verified: `asyncio.wait_for()` catches `asyncio.TimeoutError`; bridge posts `AgentTimeout` event to queue; the other agent's task continues independently because each runs in its own `asyncio.create_task()` |
| AGENT-04 | If an agent returns malformed output, user sees a clear error and the session does not crash | Verified: non-zero exit code or `RuntimeError` from stream coroutine → bridge posts `AgentError` event; other agent unaffected; queue consumer displays error without propagating exception |
</phase_requirements>

---

## Summary

Phase 1 builds the `tui/` package skeleton and the async streaming bridge that fans out to exactly 2 agent subprocesses concurrently, collects their raw text output through a typed event queue, and reports errors and timeouts cleanly — all verified via a test harness that uses a fake `AgentRunner` instead of real CLI tools.

The entire domain is Python stdlib. No new runtime dependencies are required. `asyncio.create_subprocess_exec` launches both agents as concurrent `asyncio.Task` instances. PTY mode (`pty.openpty()`) provides each subprocess a fake terminal so agents that detect non-TTY stdout and disable output buffering will stream correctly. If `pty` is unavailable (uncommon on macOS/Linux but possible in some CI environments), the bridge falls back to `asyncio.subprocess.PIPE` with a logged warning. A typed `asyncio.Queue` is the sole interface between subprocess I/O and any consumer — no widget or test ever touches a subprocess handle directly.

All patterns were verified with working Python code on Python 3.14. PTY streaming, concurrent fan-out, error containment, and timeout handling all work as expected and have been demonstrated. The test harness design uses a `FakeAgentRunner` that implements the same async generator interface as the real subprocess runner — Phase 1 tests never need a real terminal or a real `claude`/`codex` binary.

**Primary recommendation:** Use `asyncio.create_subprocess_exec` with PTY slave as stdout, `os.read()` on the master fd via `loop.add_reader()`, and a frozen dataclass event bus posted to `asyncio.Queue`. Tests use a `FakeAgentRunner` async generator and `pytest-asyncio` 0.25.x with `asyncio_mode = "auto"`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python 3.10+ | Subprocess fan-out, event loop, Queue, Task | No external dep; native async I/O; create_subprocess_exec pairs directly with loop.add_reader |
| `pty` (stdlib) | Python 3.10+ | Open PTY master/slave pair for subprocess stdout | Required to prevent stdout buffering when agents detect non-TTY; no external dep |
| `os` (stdlib) | Python 3.10+ | `os.read()`, `os.close()`, `fcntl` for non-blocking fd | Raw fd I/O for PTY master; stdlib only |
| `fcntl` (stdlib) | Python 3.10+ | Set `O_NONBLOCK` on PTY master fd | Required for non-blocking `os.read()` in event loop |
| `dataclasses` (stdlib) | Python 3.10+ | Immutable frozen dataclasses for event bus types | Type-safe, hashable, zero-cost compared to dicts |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-asyncio` | 0.25.x | `asyncio_mode = "auto"` marks all `async def` tests automatically | Required once async tests are introduced; without it, must wrap every test in `asyncio.run()` |
| `pytest` | 8.0+ | Test runner | Already in project dev dependencies |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.create_subprocess_exec` + `loop.add_reader` | `asyncio.StreamReader` via PIPE | PIPE cannot be passed a raw fd; PTY master requires raw fd I/O — `loop.add_reader` is the only correct approach for PTY mode |
| `loop.add_reader` for PTY master | `asyncio.get_event_loop().connect_read_pipe()` | `connect_read_pipe` works with file-like objects, not raw fds; requires wrapping which adds complexity |
| `pytest-asyncio` | Plain `asyncio.run()` wrapper per test | Works but requires boilerplate wrapper for every async test; `pytest-asyncio` with auto mode is cleaner |
| PTY-first | PIPE-only | Real CLI agents (claude, aider) detect non-TTY stdout and buffer output, breaking streaming; PTY is required for the target use case |

**Installation:**
```bash
pip install pytest-asyncio>=0.25,<2.0
```

Only `pytest-asyncio` is a new dependency. All other libraries are Python stdlib.

Update `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.25,<2.0"]

[tool.pytest.ini_options]
pythonpath = ["src"]
addopts = "-q"
asyncio_mode = "auto"
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── disagree_v1/          # Existing core — do NOT modify
│   ├── models.py
│   ├── orchestrator.py
│   ├── adapters.py
│   ├── classifier.py
│   ├── adjudication.py
│   ├── store.py
│   ├── presets.py
│   ├── cli.py
│   ├── launch.py
│   └── launcher.py
└── tui/                  # New package — Phase 1 creates these 3 files
    ├── __init__.py
    ├── event_bus.py      # Frozen dataclass event types
    └── bridge.py         # StreamingBridge: fan-out, PTY/pipe, queue

tests/
├── test_v1_flow.py       # Existing — do NOT modify
└── tui/
    ├── __init__.py
    └── test_bridge.py    # New: Phase 1 bridge tests with FakeAgentRunner
```

The `tui/` package has no imports from `disagree_v1/` in Phase 1. The bridge pattern is standalone and independently testable.

---

### Pattern 1: Typed Event Bus (Frozen Dataclasses)

**What:** All bridge output is expressed as frozen dataclasses posted to an `asyncio.Queue`. Consumers pattern-match on the `type` literal field.

**When to use:** Always — this is the sole interface between bridge and all consumers (test assertions, TUI widgets in later phases).

**Example:**
```python
# src/tui/event_bus.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Union


@dataclass(frozen=True)
class AgentSpec:
    name: str     # e.g., "claude"
    command: str  # executable name, e.g., "claude"
    args: tuple[str, ...] = ()

    def build_argv(self, prompt: str) -> list[str]:
        return [self.command, *self.args, prompt]


@dataclass(frozen=True)
class TokenChunk:
    agent: str
    text: str
    type: Literal["token"] = "token"


@dataclass(frozen=True)
class AgentDone:
    agent: str
    full_text: str
    exit_code: int
    type: Literal["done"] = "done"


@dataclass(frozen=True)
class AgentError:
    agent: str
    message: str
    exit_code: int
    type: Literal["error"] = "error"


@dataclass(frozen=True)
class AgentTimeout:
    agent: str
    type: Literal["timeout"] = "timeout"


BridgeEvent = Union[TokenChunk, AgentDone, AgentError, AgentTimeout]
```

---

### Pattern 2: PTY-First Subprocess Streaming

**What:** Launch subprocess with PTY slave as stdout/stderr. Read from PTY master via `loop.add_reader()`. Fall back to `asyncio.subprocess.PIPE` if PTY is unavailable.

**When to use:** For every real subprocess invocation. FakeAgentRunner bypasses this entirely in tests.

**Key facts verified:**
- PTY produces `\r\n` line endings — normalize by replacing `b'\r\n'` with `b'\n'` before posting to queue.
- PTY master fd must be set `O_NONBLOCK` before adding to event loop.
- Close slave fd in parent immediately after `create_subprocess_exec` returns.
- `loop.add_reader()` fires the callback when data is available — use `os.read(master_fd, 4096)`.
- After `proc.wait()`, sleep `0.05s` then remove reader and do a final drain loop.

**Example — PTY mode:**
```python
# Verified working on Python 3.14
import asyncio, os, pty, fcntl

async def _stream_pty(spec: AgentSpec, prompt: str, timeout: float, q: asyncio.Queue) -> int:
    master_fd, slave_fd = pty.openpty()
    # Make master non-blocking for event loop
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    proc = await asyncio.create_subprocess_exec(
        *spec.build_argv(prompt),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=slave_fd,
        stderr=slave_fd,
    )
    os.close(slave_fd)  # Parent does not need slave; child has it

    loop = asyncio.get_running_loop()
    chunks: list[bytes] = []

    def _on_readable() -> None:
        try:
            data = os.read(master_fd, 4096)
            if data:
                chunks.append(data)
                # Normalize CRLF and post line-by-line to queue
                text = data.replace(b"\r\n", b"\n").decode(errors="replace")
                for line in text.splitlines():
                    if line:
                        q.put_nowait(TokenChunk(agent=spec.name, text=line))
        except (OSError, BlockingIOError):
            loop.remove_reader(master_fd)

    loop.add_reader(master_fd, _on_readable)

    timed_out = False
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        timed_out = True
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
    finally:
        await asyncio.sleep(0.05)  # Drain remaining data
        loop.remove_reader(master_fd)
        # Final drain
        try:
            while True:
                data = os.read(master_fd, 4096)
                if not data:
                    break
                chunks.append(data)
                text = data.replace(b"\r\n", b"\n").decode(errors="replace")
                for line in text.splitlines():
                    if line:
                        q.put_nowait(TokenChunk(agent=spec.name, text=line))
        except (OSError, BlockingIOError):
            pass
        os.close(master_fd)

    if timed_out:
        await q.put(AgentTimeout(agent=spec.name))
        return -1

    if proc.returncode != 0:
        await q.put(AgentError(
            agent=spec.name,
            message=f"{spec.name} exited with code {proc.returncode}",
            exit_code=proc.returncode,
        ))
        return proc.returncode

    full_text = b"".join(chunks).replace(b"\r\n", b"\n").decode(errors="replace")
    await q.put(AgentDone(agent=spec.name, full_text=full_text, exit_code=0))
    return 0
```

**Example — PIPE fallback:**
```python
# Verified working on Python 3.14
async def _stream_pipe(spec: AgentSpec, prompt: str, timeout: float, q: asyncio.Queue) -> int:
    proc = await asyncio.create_subprocess_exec(
        *spec.build_argv(prompt),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    collected: list[str] = []
    timed_out = False

    async def _read() -> None:
        async for raw_line in proc.stdout:
            line = raw_line.decode(errors="replace").rstrip()
            if line:
                collected.append(line)
                await q.put(TokenChunk(agent=spec.name, text=line))

    try:
        await asyncio.wait_for(_read(), timeout=timeout)
    except asyncio.TimeoutError:
        timed_out = True
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

    await proc.wait()

    if timed_out:
        await q.put(AgentTimeout(agent=spec.name))
        return -1

    if proc.returncode != 0:
        await q.put(AgentError(
            agent=spec.name,
            message=f"{spec.name} exited with code {proc.returncode}",
            exit_code=proc.returncode,
        ))
        return proc.returncode

    await q.put(AgentDone(agent=spec.name, full_text="\n".join(collected), exit_code=0))
    return 0
```

---

### Pattern 3: Concurrent Fan-Out (Exactly 2 Agents)

**What:** Both agents are launched as independent `asyncio.Task` instances. Each task posts to the same shared queue. The bridge consumer counts terminal events (`done`, `error`, `timeout`) until it reaches 2.

**Key fact verified:** One agent task failing (non-zero exit or exception) does NOT affect the other agent task. Tasks are fully isolated.

**Example:**
```python
# Verified working on Python 3.14
async def run_bridge(
    prompt: str,
    spec_a: AgentSpec,
    spec_b: AgentSpec,
    timeout: float = 30.0,
    use_pty: bool = True,
) -> list[BridgeEvent]:
    q: asyncio.Queue[BridgeEvent] = asyncio.Queue()

    stream_fn = _stream_pty if use_pty else _stream_pipe

    # Fan out: both tasks start immediately, neither waits for the other
    task_a = asyncio.create_task(stream_fn(spec_a, prompt, timeout, q))
    task_b = asyncio.create_task(stream_fn(spec_b, prompt, timeout, q))

    events: list[BridgeEvent] = []
    done_count = 0
    while done_count < 2:
        event = await q.get()
        events.append(event)
        if event.type in ("done", "error", "timeout"):
            done_count += 1

    # Both terminal events received; tasks must already be done
    await asyncio.gather(task_a, task_b)
    return events
```

---

### Pattern 4: FakeAgentRunner for Test Harness

**What:** An async generator that yields lines with configurable delay and optional failure. Tests inject this instead of real subprocess runners. No real CLI tool required.

**When to use:** All Phase 1 tests. Tests are pure asyncio — no PTY, no subprocess, no real binaries.

**Example:**
```python
# tests/tui/test_bridge.py

import asyncio
import pytest
from tui.event_bus import AgentSpec, TokenChunk, AgentDone, AgentError, AgentTimeout, BridgeEvent


class FakeAgentRunner:
    """Drop-in replacement for real subprocess runner. Used in all Phase 1 tests."""

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
            await q.put(AgentDone(agent=runner.name, full_text="\n".join(collected), exit_code=0))
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


# Tests (pytest-asyncio auto mode — no decorator needed)

async def test_both_agents_produce_tokens():
    """Both agents stream tokens when both succeed."""
    runner_a = FakeAgentRunner("claude", ["Line A1", "Line A2"])
    runner_b = FakeAgentRunner("codex", ["Line B1"])

    events = await run_bridge_with_fakes("test prompt", runner_a, runner_b)

    token_agents = {e.agent for e in events if e.type == "token"}
    assert "claude" in token_agents
    assert "codex" in token_agents


async def test_error_does_not_kill_surviving_agent():
    """When one agent errors, the other completes normally."""
    runner_a = FakeAgentRunner("claude", ["A1", "A2"], exit_code=0, delay=0.05)
    runner_b = FakeAgentRunner("codex", ["B1"], exit_code=1, delay=0.01)

    events = await run_bridge_with_fakes("test prompt", runner_a, runner_b)

    error_events = [e for e in events if e.type == "error"]
    done_events = [e for e in events if e.type == "done"]
    assert any(e.agent == "codex" for e in error_events)
    assert any(e.agent == "claude" for e in done_events)


async def test_timeout_does_not_kill_surviving_agent():
    """When one agent times out, the other completes normally."""
    runner_a = FakeAgentRunner("claude", ["A1"], delay=9999.0)  # Will hang
    runner_b = FakeAgentRunner("codex", ["B1"], delay=0.01)

    events = await run_bridge_with_fakes("test prompt", runner_a, runner_b, timeout=0.1)

    timeout_events = [e for e in events if e.type == "timeout"]
    done_events = [e for e in events if e.type == "done"]
    assert any(e.agent == "claude" for e in timeout_events)
    assert any(e.agent == "codex" for e in done_events)


async def test_terminal_events_exactly_two():
    """Bridge always emits exactly 2 terminal events (done/error/timeout)."""
    runner_a = FakeAgentRunner("claude", ["A1"])
    runner_b = FakeAgentRunner("codex", ["B1"])

    events = await run_bridge_with_fakes("prompt", runner_a, runner_b)

    terminal = [e for e in events if e.type in ("done", "error", "timeout")]
    assert len(terminal) == 2


async def test_done_event_contains_full_text():
    """AgentDone contains the complete accumulated text."""
    runner = FakeAgentRunner("claude", ["Line 1", "Line 2", "Line 3"])
    runner_b = FakeAgentRunner("codex", [])

    events = await run_bridge_with_fakes("prompt", runner, runner_b)

    done = next(e for e in events if e.type == "done" and e.agent == "claude")
    assert "Line 1" in done.full_text
    assert "Line 2" in done.full_text
    assert "Line 3" in done.full_text
```

---

### Pattern 5: PTY Availability Detection

**What:** Try `pty.openpty()` at bridge startup; catch `OSError` and fall back to PIPE mode with a printed warning.

**Example:**
```python
import pty
import warnings

def _pty_available() -> bool:
    try:
        import pty as _pty
        master_fd, slave_fd = _pty.openpty()
        import os as _os
        _os.close(master_fd)
        _os.close(slave_fd)
        return True
    except (OSError, AttributeError):
        return False

# At bridge construction time:
USE_PTY = _pty_available()
if not USE_PTY:
    warnings.warn(
        "PTY unavailable — falling back to PIPE mode. "
        "Agent output may be buffered and streaming may be delayed.",
        RuntimeWarning,
        stacklevel=2,
    )
```

---

### Anti-Patterns to Avoid

- **Blocking `os.read()` in async context without `O_NONBLOCK`:** PTY master fd defaults to blocking mode. Without `fcntl.fcntl(fd, F_SETFL, flags | O_NONBLOCK)`, `os.read()` blocks the event loop — all concurrency stops. Set `O_NONBLOCK` before calling `loop.add_reader()`.

- **Not closing slave fd in parent after fork:** The subprocess holds the slave fd open. If the parent also holds it open, the PTY master never reaches EOF — the reader loop never terminates. Always `os.close(slave_fd)` immediately after `create_subprocess_exec` returns.

- **Using `proc.communicate()` for streaming:** `communicate()` buffers all output until process exit — it cannot stream. Use `readline()` loop for PIPE mode or `loop.add_reader()` for PTY mode.

- **Calling `proc.wait()` inside a `with asyncio.timeout()` block without also terminating the process:** On `TimeoutError`, the process continues running. Always call `proc.terminate()` followed by `proc.wait()` (with kill fallback) after timeout.

- **Sharing mutable state between agent tasks:** Each agent task must write only to the shared queue — no shared lists, no shared dicts. The queue is the only thread/task-safe interface.

- **N-agent generalization:** The concurrency model is explicitly 2 agents. Do not parameterize `run_bridge` with `agents: list[AgentSpec]` in Phase 1. The hardcoded-2 design is intentional and simpler to test. Phase 5 will extend if needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async subprocess streaming | Custom thread-based reader | `asyncio.create_subprocess_exec` + `loop.add_reader` | Edge cases in thread safety, fd lifetime, EOF detection — all solved by stdlib |
| Non-blocking fd reads | Busy-poll loop | `fcntl.F_SETFL` + `O_NONBLOCK` + `loop.add_reader` | Busy-polling burns CPU and blocks the event loop; `add_reader` is callback-driven |
| Timeout enforcement | Manual `asyncio.sleep` and flag | `asyncio.wait_for(proc.wait(), timeout=...)` | Correct cancellation semantics, tested by asyncio internals |
| Subprocess cleanup | No cleanup | `proc.terminate()` + `proc.wait()` with kill fallback | Without explicit cleanup, subprocesses become zombies that hold the PTY slave open |
| Event type discrimination | String `type` field in dict | Frozen dataclass with `Literal` type field | Type-safe, IDE-completable, hashable, zero-cost vs dict |

**Key insight:** Every item in this table is a source of subtle bugs that appear only under timing or resource pressure. The stdlib approaches have been battle-tested across millions of Python processes. Hand-rolling alternatives in a streaming bridge that must handle concurrent agent failures is not worth the risk.

---

## Common Pitfalls

### Pitfall 1: PTY Master Blocks Event Loop

**What goes wrong:** `os.read(master_fd, 4096)` blocks if the fd is in blocking mode and no data is available — the event loop freezes, and both agent tasks stall.

**Why it happens:** `pty.openpty()` returns file descriptors in blocking mode by default.

**How to avoid:** Always call `fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)` immediately after `pty.openpty()`, before passing the fd to `loop.add_reader()`. Catch `BlockingIOError` in the reader callback.

**Warning signs:** Both agent streams pause simultaneously; only one line appears and then nothing.

---

### Pitfall 2: Slave FD Held Open in Parent Causes Hung Reader

**What goes wrong:** After `proc.wait()` returns, the PTY reader callback never stops firing (or fires with empty data repeatedly) because the master sees the slave still open. `os.read()` does not return 0 bytes to signal EOF while any process holds the slave fd.

**Why it happens:** The parent process still holds the slave fd open after `create_subprocess_exec` returns. The PTY layer sees two holders of the slave end (child + parent), so the master does not EOF.

**How to avoid:** `os.close(slave_fd)` in the parent immediately after `create_subprocess_exec` returns. Verified: without this, the reader does not terminate cleanly.

**Warning signs:** Reader keeps running after `proc.wait()` returns; `asyncio.sleep(0.05)` drain takes longer than expected.

---

### Pitfall 3: CRLF in PTY Output

**What goes wrong:** PTY canonical mode converts `\n` to `\r\n`. Downstream text processing that splits on `\n` produces lines with trailing `\r`. ANSI sequences at line boundaries may appear broken.

**Why it happens:** PTY emulates a real terminal, which uses CRLF conventions.

**How to avoid:** Always normalize `data.replace(b"\r\n", b"\n")` on every chunk before decoding and splitting into lines.

**Warning signs:** Lines in queue have trailing `\r`; `"Done.\r"` instead of `"Done."`.

---

### Pitfall 4: Zombie Subprocesses on Exit

**What goes wrong:** If the event loop or test tears down before `proc.wait()` completes, the subprocess remains a zombie (PCB held by kernel, holding slave fd open). In tests, this can cause subsequent tests to behave unexpectedly.

**Why it happens:** No explicit cleanup when the bridge task is cancelled or times out.

**How to avoid:** Always pair `proc.terminate()` with `await proc.wait()` (with a `proc.kill()` fallback) in a `finally` block. The timeout handler in the bridge must do this.

**Warning signs:** After test run, `ps aux | grep claude` shows zombie processes; test suite hangs on cleanup.

---

### Pitfall 5: Task Cancellation Leaks

**What goes wrong:** If the outer consumer cancels before receiving 2 terminal events, `task_a` and `task_b` may still be running. The subprocess stays alive and the PTY master fd stays open.

**Why it happens:** `asyncio.create_task` schedules tasks independently. Cancelling the consumer does not cancel the tasks.

**How to avoid:** In production code (not test harness), the bridge should expose a `cancel()` method that calls `task_a.cancel()` and `task_b.cancel()` and then terminates both subprocesses. For Phase 1, this is a known gap — the test harness completes normally in all test cases. Flag as a Phase 3 concern (when bridge is wired to TUI with `Ctrl-C` exit).

**Warning signs:** Test suite passes but processes leak; memory grows across test runs.

---

### Pitfall 6: pytest-asyncio Mode Mismatch

**What goes wrong:** `pytest-asyncio` 0.21+ defaults to `strict` mode. Without `asyncio_mode = "auto"` in `pyproject.toml`, async test functions are collected but not run as asyncio tests — they appear to pass trivially (coroutine object is truthy) without actually running.

**Why it happens:** In strict mode, async tests must be explicitly marked with `@pytest.mark.asyncio`.

**How to avoid:** Set `asyncio_mode = "auto"` in `[tool.pytest.ini_options]` in `pyproject.toml`. This applies to the entire project. With auto mode, all `async def test_*` functions are treated as asyncio tests automatically.

**Warning signs:** Tests "pass" in 0.001s each with no assertions running; removing `assert False` does not cause failure.

---

## Code Examples

Verified patterns from working Python code (Python 3.14, verified 2026-02-21):

### Concurrent 2-Agent Fan-Out with Typed Queue

```python
# Verified: events interleave correctly, slower agent does not block faster one
import asyncio, os, pty, fcntl

# Both tasks start immediately; queue receives events from both concurrently
task_a = asyncio.create_task(stream_agent(spec_a, prompt, timeout, q))
task_b = asyncio.create_task(stream_agent(spec_b, prompt, timeout, q))

done_count = 0
events = []
while done_count < 2:
    event = await q.get()
    events.append(event)
    if event.type in ("done", "error", "timeout"):
        done_count += 1

await asyncio.gather(task_a, task_b)
```

### PTY Master Async Reader (Verified Pattern)

```python
# Verified: produces correct output; CRLF normalized; O_NONBLOCK essential
master_fd, slave_fd = pty.openpty()
flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

proc = await asyncio.create_subprocess_exec(
    *argv,
    stdin=asyncio.subprocess.DEVNULL,
    stdout=slave_fd,
    stderr=slave_fd,
)
os.close(slave_fd)  # Critical: parent must close slave

loop = asyncio.get_running_loop()

def _on_readable():
    try:
        data = os.read(master_fd, 4096)
        if data:
            text = data.replace(b"\r\n", b"\n").decode(errors="replace")
            for line in text.splitlines():
                if line:
                    q.put_nowait(TokenChunk(agent=name, text=line))
    except (OSError, BlockingIOError):
        loop.remove_reader(master_fd)

loop.add_reader(master_fd, _on_readable)
```

### Timeout with Clean Subprocess Termination (Verified Pattern)

```python
# Verified: timeout fires; proc is terminated; other task continues unaffected
timed_out = False
try:
    await asyncio.wait_for(proc.wait(), timeout=timeout)
except asyncio.TimeoutError:
    timed_out = True
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

# Post terminal event based on outcome
if timed_out:
    await q.put(AgentTimeout(agent=name))
elif proc.returncode != 0:
    await q.put(AgentError(agent=name, message=f"exit {proc.returncode}", exit_code=proc.returncode))
else:
    await q.put(AgentDone(agent=name, full_text=collected, exit_code=0))
```

### pyproject.toml Update for pytest-asyncio

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.25,<2.0"]

[tool.pytest.ini_options]
pythonpath = ["src"]
addopts = "-q"
asyncio_mode = "auto"
```

---

## Claude's Discretion Recommendations

### Chunk Granularity: Use Complete Lines

**Recommendation:** Post complete lines (via `str.splitlines()` on each PTY chunk) rather than raw bytes chunks.

**Reasoning:**
1. Raw byte chunks can split mid-ANSI-sequence (e.g., `\x1b[1;3` / `2mHello`). Splitting corrupts the escape sequence for any downstream renderer.
2. Lines are a natural unit for the test harness — `FakeAgentRunner` yields lines, so queue assertions are line-granular and readable.
3. Lines are a natural unit for the TUI — `RichLog.write_line()` in Phase 3 expects complete lines.
4. The performance difference is negligible for human-speed agent output.

**When to reconsider:** If Phase 3 TUI integration reveals that agents emit very long lines (e.g., a single 100KB JSON blob), switch to chunk streaming with a reassembly buffer. For Phase 1, lines are correct.

---

### Command Template Structure: Use `AgentSpec` Frozen Dataclass

**Recommendation:** Define `AgentSpec(name, command, args)` as a frozen dataclass in `event_bus.py`. Hardcode two default instances in `bridge.py`. Do NOT read from config files in Phase 1.

**Reasoning:**
1. A frozen dataclass is immutable and hashable — safe to pass across async boundaries.
2. `AgentSpec.build_argv(prompt)` encapsulates the argument construction — tests can assert on `argv` without knowing the bridge internals.
3. Phase 5 extends `AgentSpec` with additional fields (`timeout_override`, `env`, etc.) without changing `bridge.py`. This satisfies OCP.
4. Hardcoded defaults in Phase 1 mean zero config parsing code — simpler, fewer failure modes, easier to test.

```python
# Default specs for Phase 1 — hardcoded, overridable in tests
CLAUDE = AgentSpec(name="claude", command="claude")
CODEX = AgentSpec(name="codex", command="codex")
```

---

## State of the Art

| Old Approach (disagree_v1) | Current Approach (Phase 1) | Impact |
|----------------------------|---------------------------|--------|
| `ThreadPoolExecutor` + `subprocess.run()` (blocking) | `asyncio.create_task` + `asyncio.create_subprocess_exec` (async) | Non-blocking I/O; event loop handles both agents concurrently without threads |
| `CommandJsonAdapter` parses JSON from agent stdout | Raw text streaming — no JSON schema | Agents stream naturally; no output format contract with CLI tools |
| `subprocess.run(timeout=90)` (global blocking) | `asyncio.wait_for(proc.wait(), timeout=...)` per task | Each agent has its own timeout that does not block the event loop or the other agent |
| Batch collect → classify | Stream tokens live → classify after both done | Tokens visible in real-time; classification still happens after both complete (Phase 1 invariant) |
| `stdin=None` (inherits parent TTY) | `stdin=asyncio.subprocess.DEVNULL` | Prevents TUI stdin conflict; subprocess cannot read from terminal |

**Deprecated/outdated from disagree_v1:**
- `CommandJsonAdapter`: dropped — agents invoked with raw text, no JSON schema
- `build_claude_codex_commands()` from `presets.py`: dropped — command templates replaced by `AgentSpec`
- `ThreadPoolExecutor`: dropped — replaced by `asyncio.create_task`
- JSON schema in `schemas/`: not used by bridge — agents emit plain text

---

## Open Questions

1. **Which real CLI agents require PTY to stream?**
   - What we know: `claude` CLI detects non-TTY stdout and buffers or disables streaming. PTY prevents this. Other agents (codex, aider) likely behave similarly.
   - What's unclear: The exact behavior of each real agent binary has not been spiked yet. The STATE.md flags this: "some CLI agents (aider, claude) detect non-TTY stdout and disable streaming — needs a real spike per agent in Phase 1."
   - Recommendation: Phase 1 plan should include one task that runs the real `claude` binary with PTY mode and with PIPE mode and documents the observed buffering behavior. This is the only real-subprocess work in Phase 1 — all bridge logic is proven via FakeAgentRunner first.

2. **`asyncio_default_fixture_loop_scope` deprecation warning**
   - What we know: `pytest-asyncio` 0.21+ emits a `DeprecationWarning` if `asyncio_default_fixture_loop_scope` is unset. In 0.25.x, it still defaults to fixture scope but warns. In a future version it will default to `function`.
   - What's unclear: Whether the warning will appear in CI output and whether it should be suppressed or configured.
   - Recommendation: Set `asyncio_default_fixture_loop_scope = "function"` in `pyproject.toml` to silence the warning and opt into the future default explicitly.

3. **Package namespace for `tui/`**
   - What we know: `pyproject.toml` currently uses `pythonpath = ["src"]` with no explicit `[tool.setuptools.packages]`. `disagree_v1` is discovered automatically.
   - What's unclear: Whether `tui` should live inside `disagree_v1.tui` or as a sibling `tui` package.
   - Recommendation: Start with `src/tui/` as a sibling package (same level as `disagree_v1`). This keeps a clean separation — the TUI layer is not part of the old core. Update `pyproject.toml` to rename the project to `agent-bureau` in Phase 1 since `disagree-v1` no longer reflects the product.

---

## Sources

### Primary (HIGH confidence)

- Python 3.14 stdlib docs — `asyncio.create_subprocess_exec`, `Process.wait`, `StreamReader.readline` (https://docs.python.org/3/library/asyncio-subprocess.html)
- Python 3.14 stdlib docs — `pty.openpty`, `os.read`, `fcntl.F_SETFL` — verified by running live code
- All code examples in this document were executed and verified on Python 3.14.3 (macOS darwin 24.6.0) on 2026-02-21

### Secondary (MEDIUM confidence)

- pytest-asyncio 0.25.x / 1.x configuration — `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope` — verified via PyPI index (`pytest-asyncio` latest: 1.3.0) and official docs (https://pytest-asyncio.readthedocs.io/en/stable/reference/configuration.html)
- PTY buffering behavior of real CLI agents — documented in project STATE.md as a known risk requiring a spike; not independently verified in this research

### Prior Research (HIGH confidence — already incorporated)

- `.planning/research/SUMMARY.md` — architecture patterns, pitfalls, stack decisions from prior domain research phase
- All 12 pitfalls from `PITFALLS.md` synthesized in SUMMARY.md

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib; only new dep is pytest-asyncio which is well-documented
- Architecture: HIGH — all patterns verified with working code on target Python version
- Pitfalls: HIGH — grounded in verified code experiments and prior domain research
- PTY agent buffering behavior: MEDIUM — known risk, flagged for spike in Phase 1 plan

**Research date:** 2026-02-21
**Valid until:** 2026-05-21 (asyncio stdlib is stable; pytest-asyncio major changes unlikely in 90 days)
