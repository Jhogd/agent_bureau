"""
Async streaming bridge — real subprocess fan-out.

PTY-first: gives each agent subprocess a fake terminal so agents stream output
exactly as they would in a real terminal (no stdout buffering).

Falls back to PIPE mode with a RuntimeWarning if PTY is unavailable (CI, etc.).

ANSI pass-through: raw bytes are decoded and passed through unchanged.
The TUI renders agent colors directly — do NOT strip ANSI escape sequences.
"""

from __future__ import annotations

import asyncio
import fcntl
import os
import warnings
from typing import Optional

from tui.event_bus import (
    AgentSpec,
    AgentDone,
    AgentError,
    AgentTimeout,
    BridgeEvent,
    TokenChunk,
)

# ---------------------------------------------------------------------------
# Public agent defaults
# ---------------------------------------------------------------------------

CLAUDE = AgentSpec(name="claude", command="claude", args=("-p",))
# codex exec = non-interactive mode; read-only sandbox prevents file writes during debate
CODEX = AgentSpec(name="codex", command="codex", args=("exec", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check"))


# ---------------------------------------------------------------------------
# PTY availability check
# ---------------------------------------------------------------------------


def _pty_available() -> bool:
    """Return True if pty.openpty() works on this system."""
    try:
        import pty
        master_fd, slave_fd = pty.openpty()
        os.close(master_fd)
        os.close(slave_fd)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# PTY streaming
# ---------------------------------------------------------------------------


async def _stream_pty(
    spec: AgentSpec,
    prompt: str,
    timeout: float,
    q: asyncio.Queue[BridgeEvent],
) -> None:
    """Stream agent subprocess output via PTY (fake terminal)."""
    import pty

    master_fd, slave_fd = pty.openpty()

    # Set O_NONBLOCK on master before add_reader so reads never block the loop.
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    proc = await asyncio.create_subprocess_exec(
        *spec.build_argv(prompt),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=slave_fd,
        stderr=slave_fd,
    )

    # Close slave_fd in the parent immediately after create_subprocess_exec.
    os.close(slave_fd)

    loop = asyncio.get_event_loop()
    collected: list[str] = []
    read_done = asyncio.Event()

    def _on_readable() -> None:
        try:
            data = os.read(master_fd, 4096)
        except OSError:
            # EIO on Linux when slave end closes; expected at EOF.
            loop.remove_reader(master_fd)
            read_done.set()
            return
        if not data:
            loop.remove_reader(master_fd)
            read_done.set()
            return
        # CRLF normalization: PTY uses CRLF line endings.
        text = data.replace(b"\r\n", b"\n").decode("utf-8", errors="replace")
        for line in text.splitlines():
            if line:
                collected.append(line)
                q.put_nowait(TokenChunk(agent=spec.name, text=line))

    loop.add_reader(master_fd, _on_readable)

    try:
        async with asyncio.timeout(timeout):
            await read_done.wait()
            await proc.wait()
    except asyncio.TimeoutError:
        loop.remove_reader(master_fd)
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        await q.put(AgentTimeout(agent=spec.name))
    except Exception as exc:
        loop.remove_reader(master_fd)
        await q.put(AgentError(agent=spec.name, message=str(exc), exit_code=-1))
    else:
        if proc.returncode == 0:
            await q.put(
                AgentDone(
                    agent=spec.name,
                    full_text="\n".join(collected),
                    exit_code=proc.returncode,
                )
            )
        else:
            await q.put(
                AgentError(
                    agent=spec.name,
                    message=f"exited with code {proc.returncode}",
                    exit_code=proc.returncode,
                )
            )
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# PIPE streaming (fallback)
# ---------------------------------------------------------------------------


async def _stream_pipe(
    spec: AgentSpec,
    prompt: str,
    timeout: float,
    q: asyncio.Queue[BridgeEvent],
) -> None:
    """Stream agent subprocess output via PIPE (fallback — may buffer)."""
    proc = await asyncio.create_subprocess_exec(
        *spec.build_argv(prompt),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    assert proc.stdout is not None
    collected: list[str] = []

    async def _read_lines() -> None:
        while True:
            line_bytes = await proc.stdout.readline()  # type: ignore[union-attr]
            if not line_bytes:
                break
            # ANSI pass-through — decode only, do NOT strip escape sequences.
            line = line_bytes.decode("utf-8", errors="replace").rstrip("\n")
            if line:
                collected.append(line)
                await q.put(TokenChunk(agent=spec.name, text=line))

    try:
        async with asyncio.timeout(timeout):
            await _read_lines()
            await proc.wait()
    except asyncio.TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        await q.put(AgentTimeout(agent=spec.name))
        return
    except Exception as exc:
        await q.put(AgentError(agent=spec.name, message=str(exc), exit_code=-1))
        return

    if proc.returncode == 0:
        await q.put(
            AgentDone(
                agent=spec.name,
                full_text="\n".join(collected),
                exit_code=proc.returncode,
            )
        )
    else:
        await q.put(
            AgentError(
                agent=spec.name,
                message=f"exited with code {proc.returncode}",
                exit_code=proc.returncode,
            )
        )


# ---------------------------------------------------------------------------
# Public fan-out entry point
# ---------------------------------------------------------------------------


async def run_bridge(
    prompt: str,
    spec_a: AgentSpec = CLAUDE,
    spec_b: AgentSpec = CODEX,
    timeout: float = 60.0,
    use_pty: Optional[bool] = None,
) -> list[BridgeEvent]:
    """
    Fan-out to exactly 2 agent subprocesses concurrently.

    Both agents start immediately. Events are collected from a shared asyncio.Queue
    until exactly 2 terminal events (done/error/timeout) are received.

    Args:
        prompt:  The prompt string forwarded to both agents.
        spec_a:  AgentSpec for the first agent (default: CLAUDE).
        spec_b:  AgentSpec for the second agent (default: CODEX).
        timeout: Global per-agent timeout in seconds.
        use_pty: Force PTY mode (True), PIPE mode (False), or auto-detect (None).

    Returns:
        Ordered list of BridgeEvent instances (TokenChunk + terminal events).
    """
    if use_pty is None:
        use_pty = _pty_available()

    if use_pty:
        _stream = _stream_pty
    else:
        warnings.warn(
            "PTY unavailable — falling back to PIPE mode. "
            "Agent output may be buffered.",
            RuntimeWarning,
            stacklevel=2,
        )
        _stream = _stream_pipe

    q: asyncio.Queue[BridgeEvent] = asyncio.Queue()

    task_a = asyncio.create_task(_stream(spec_a, prompt, timeout, q))
    task_b = asyncio.create_task(_stream(spec_b, prompt, timeout, q))

    events: list[BridgeEvent] = []
    done_count = 0
    while done_count < 2:
        event = await q.get()
        events.append(event)
        if event.type in ("done", "error", "timeout"):
            done_count += 1

    await asyncio.gather(task_a, task_b)
    return events
