# PITFALLS.md — TUI + Subprocess Streaming for Multi-Agent CLI

**Research type:** Project Research — Pitfalls dimension
**Domain:** Python TUI that streams multiple AI CLI agents via subprocess in parallel
**Date:** 2026-02-21

---

## Overview

This document captures common and critical mistakes made in Python TUI projects that stream subprocess output, manage concurrent panes, and need clean install/packaging. Each pitfall includes warning signs, a prevention strategy, and a phase mapping.

---

## Pitfall 1: Blocking reads on subprocess stdout stall the event loop

**Category:** Subprocess streaming
**Severity:** Critical

### What goes wrong

Using `subprocess.stdout.readline()` or `subprocess.stdout.read()` in a synchronous loop blocks the thread (or asyncio event loop) until data arrives. When two agents run in parallel, blocking on one stalls updates to the other pane entirely. The UI freezes mid-stream and appears hung.

### Warning signs

- One pane updates fine; the other only updates after the first finishes.
- `asyncio.get_event_loop().run_until_complete()` is called around a `readline()` loop.
- `threading.Thread` is created per subprocess but output is funneled through a shared non-thread-safe queue without locking.
- Profiling shows the main thread spending time in `io.BufferedReader.read`.

### Prevention strategy

Use `asyncio.create_subprocess_exec` with `asyncio.StreamReader` and read with `await stream.readline()`. Never call blocking I/O inside a coroutine. If threads are used instead of asyncio, use `queue.Queue` (thread-safe) and drain it in the TUI render loop, not directly in the thread. Assign one reader coroutine per subprocess and `asyncio.gather` them.

### Phase

Address in the first TUI streaming spike, before any pane layout work. Getting this wrong early causes a cascade of workarounds.

---

## Pitfall 2: ANSI escape codes and control sequences corrupt pane rendering

**Category:** TUI rendering
**Severity:** High

### What goes wrong

AI CLI tools (claude, codex) emit ANSI color codes, cursor movement sequences, and sometimes terminal alternate-screen escape sequences (`\x1b[?1049h`). When this raw output is written directly into a Textual or Urwid pane widget, the widget's own rendering is corrupted. Cursor jumps, color bleed across panes, and garbled text appear.

### Warning signs

- Text in panes contains literal `\x1b[` sequences or partial control codes.
- The terminal background color changes unexpectedly after agent output.
- Scrollback in one pane bleeds into another pane's content area.
- A subprocess emits `\r` carriage returns that overwrite the beginning of widget lines.

### Prevention strategy

Strip or sanitize ANSI codes before inserting into TUI widgets using a library like `strip-ansi` or a regex (`re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)`). If colored output in panes is desired, translate ANSI codes to the TUI framework's own markup (e.g., Textual's `Text` with `from_ansi()`). Explicitly test with `--no-color` flags passed to subprocesses when possible. Never pass raw subprocess stdout bytes directly to a widget's `write()` method.

### Phase

Address before the first end-to-end streaming demo. Even one unhandled escape sequence can make the pane unusable.

---

## Pitfall 3: Subprocess stdout buffering makes real-time streaming appear stalled

**Category:** Subprocess streaming
**Severity:** High

### What goes wrong

Python subprocesses buffer stdout by default when not attached to a TTY. A CLI tool that prints progress character-by-character may buffer internally and only flush in large chunks or at exit. The TUI pane appears empty for the full duration of the agent run, then floods with all output at once.

### Warning signs

- Output appears in one large burst at the end of the agent run.
- Manually running the CLI tool in a terminal shows streaming output, but via subprocess it does not.
- `proc.stdout.readline()` blocks for the entire run duration before returning.

### Prevention strategy

Pass `bufsize=0` (unbuffered) or use `bufsize=1` (line-buffered) when creating subprocesses. Use `pexpect` or a pseudo-TTY (`pty.openpty()`) to trick the subprocess into thinking it's attached to a terminal, which forces line-buffered output. As a fallback, pass `--no-buffer` or `-u` equivalent flags to the CLI tool if supported. For Python subprocesses specifically, set `PYTHONUNBUFFERED=1` in the subprocess environment.

### Phase

Address in the streaming spike, day one. Validate with a real `claude` or `codex` CLI invocation before building any TUI layout around it.

---

## Pitfall 4: Thread-unsafe state shared between TUI render loop and subprocess reader threads

**Category:** Concurrency
**Severity:** High

### What goes wrong

Subprocess reader threads write directly to shared data structures (lists, dicts, widget state) that the TUI's main thread reads during rendering. Without synchronization, partial writes cause corrupted state, missing lines, or index errors. This is subtle — it manifests as intermittent rendering glitches that are hard to reproduce.

### Warning signs

- Random `IndexError` or `KeyError` during rendering that disappears on retry.
- Output lines appear out of order in the pane.
- Lines from Agent A appear in Agent B's pane occasionally.
- The bug is not reproducible in single-agent mode.

### Prevention strategy

Use `queue.Queue` as the only communication channel between reader threads and the TUI render thread. Each subprocess gets its own `Queue`. The TUI render loop drains queues via `queue.get_nowait()` in a non-blocking poll. Never let a reader thread call any TUI widget method directly. If using asyncio throughout, use `asyncio.Queue` and `await queue.get()` inside coroutines; no threads needed.

### Phase

Establish this pattern in the streaming architecture before adding the second agent. Adding a second concurrent reader to an already-racy design multiplies the hazard.

---

## Pitfall 5: TTY/PTY requirements cause subprocess to behave differently on CI vs local

**Category:** Subprocess streaming / packaging
**Severity:** Medium-High

### What goes wrong

Some CLI tools (including `claude` CLI) detect whether they are connected to a TTY and change their output format, disable color, or refuse to run in non-interactive mode. The TUI works locally because it uses a PTY, but breaks in CI, Docker, or when piped. Conversely, using a PTY locally makes it hard to unit-test the streaming layer.

### Warning signs

- The tool runs fine interactively but hangs or produces no output when invoked via `subprocess.Popen`.
- The tool outputs `Error: stdin is not a TTY` or similar.
- Unit tests for the streaming layer require a real terminal to pass.
- CI pipeline runs the TUI tests and they fail with environment errors.

### Prevention strategy

Abstract the subprocess invocation behind an interface (`AgentRunner` protocol) so tests can inject a fake runner that emits canned output without spawning a real process. For production, use `pty.openpty()` when a TTY is required, but isolate that code to a single, tested adapter. Do not scatter PTY logic across the codebase. Document in the README which CI environments are supported.

### Phase

Define the `AgentRunner` abstraction in the first TDD cycle. The fake implementation is needed immediately for any unit tests of the streaming logic.

---

## Pitfall 6: Textual (or chosen TUI framework) version churn breaks layouts silently

**Category:** TUI framework / packaging
**Severity:** Medium

### What goes wrong

Textual's API changes frequently between minor versions. Layouts, CSS properties, and widget APIs that work in one version silently break or render differently in the next. A project without pinned dependencies ships to a user with a newer Textual version and the layout is broken.

### Warning signs

- `pip install agent-bureau` on a fresh machine produces visual glitches not present in development.
- Textual changelog includes layout or CSS breaking changes in a recent release.
- The project's `pyproject.toml` uses unpinned or overly broad version constraints like `textual>=0.1`.
- A team member on a different machine sees a different layout.

### Prevention strategy

Pin Textual to a specific minor version in `pyproject.toml` (e.g., `textual==0.70.*`). Use a lock file (`pip-tools` / `uv lock`) and commit it. Write a smoke test that launches the TUI headlessly (Textual's `pilot` testing API) and asserts key widgets are present — this catches layout regressions on version upgrades. Upgrade Textual deliberately, not passively.

### Phase

Establish pinned dependencies and lock file at project scaffolding time, before any TUI code is written.

---

## Pitfall 7: Subprocess zombie processes and dangling handles on early exit

**Category:** Subprocess lifecycle
**Severity:** High

### What goes wrong

When the user quits the TUI (Ctrl+C, `q`, or window close), subprocesses are not terminated. They continue running in the background, consuming API credits and resources. If the TUI crashes, the handles are not cleaned up and the processes become zombies. On restart, a new set of processes is spawned alongside the old ones.

### Warning signs

- `ps aux | grep claude` shows multiple `claude` processes after closing the TUI.
- API usage is higher than expected.
- A `KeyboardInterrupt` or unhandled exception in the TUI leaves no cleanup path.
- No `try/finally` or context manager wraps subprocess lifecycle.

### Prevention strategy

Use `contextlib.ExitStack` or a dedicated `AgentPool` context manager that calls `proc.terminate()` and `proc.wait()` on all managed subprocesses in its `__exit__`. Register a `signal.signal(signal.SIGTERM, ...)` handler in the main process. In Textual, override the `on_unmount` lifecycle method to trigger cleanup. Set `proc.kill()` after a timeout if `proc.terminate()` does not stop the process within a grace period.

### Phase

Implement subprocess lifecycle management as a first-class concern in the streaming spike. Do not defer it to a "cleanup pass" — it is safety-critical.

---

## Pitfall 8: Output scrollback grows unbounded and causes memory exhaustion

**Category:** TUI rendering / resource management
**Severity:** Medium

### What goes wrong

Streaming agent output is accumulated in a list or widget buffer indefinitely. Long agent runs (multi-round debates, large codebases) produce thousands of lines. Memory grows linearly with output size. On constrained machines, the TUI becomes sluggish then crashes with an OOM error.

### Warning signs

- Memory usage climbs continuously during a run.
- The TUI slows down proportionally to the amount of output received.
- A single `list` stores all streamed lines without a cap.
- `ScrollView` or `Log` widget is never truncated.

### Prevention strategy

Implement a ring buffer (e.g., `collections.deque(maxlen=N)`) for pane output, where N is configurable (default 2000 lines per pane). Only the visible window plus a modest scrollback is kept in memory. Textual's `Log` widget has a `max_lines` parameter — use it. Add a memory budget test to the smoke test suite: run a mock agent that emits 10,000 lines and assert memory stays below a threshold.

### Phase

Set the ring buffer constraint during the pane widget implementation. Leaving it unbounded and "coming back to it" rarely happens in practice.

---

## Pitfall 9: Packaging fails because the TUI depends on a terminal that pip install does not provision

**Category:** Packaging / install
**Severity:** Medium

### What goes wrong

The project works when run from the repo but the installed package (`pip install agent-bureau`) fails because:
- The entry point script is not declared in `pyproject.toml`.
- Assets (CSS files for Textual) are not included in the package data.
- The shebang line references a venv path that does not exist in the installed location.
- `importlib.resources` is not used to locate bundled assets, so they are not found after installation.

### Warning signs

- `agent-bureau` command not found after `pip install`.
- `FileNotFoundError` for a `.css` or `.tcss` file at runtime after install.
- Works via `python -m agent_bureau` but not via the `agent-bureau` entry point.
- Package not included in `[tool.poetry.packages]` or `[project.packages]`.

### Prevention strategy

Declare the entry point in `pyproject.toml` under `[project.scripts]`. Include all non-Python assets (`.tcss`, templates) in `[tool.poetry.include]` or equivalent. Reference bundled assets via `importlib.resources.files(__package__)` rather than relative `Path(__file__)` tricks. Validate packaging by installing into a fresh virtual environment as part of CI: `pip install dist/*.whl && agent-bureau --version`.

### Phase

Set up the package scaffold (`pyproject.toml`, entry point, asset inclusion) before writing any TUI code. Retrofitting packaging onto an existing codebase is tedious and error-prone.

---

## Pitfall 10: The "apply changes" step races with ongoing agent output

**Category:** Concurrency / correctness
**Severity:** High

### What goes wrong

When the user selects a winner or agents reach consensus, the code-application step begins while the losing agent's subprocess is still streaming output. The TUI tries to both render new output and apply file changes simultaneously. This causes either garbled pane updates (render happening over changed state) or partial file writes (application interrupted mid-stream).

### Warning signs

- File changes are applied but the pane still shows streaming output from an agent that should have been stopped.
- The TUI becomes unresponsive immediately after the user selects a winner.
- The applied diff is incomplete — some hunks are missing.
- Tests for the apply step pass in isolation but fail when run with a live streaming session.

### Prevention strategy

Model the debate lifecycle as an explicit state machine: `STREAMING → CONSENSUS_REACHED → AWAITING_USER → APPLYING → DONE`. Transitions are gated — the apply step only begins after all subprocesses are terminated and their queues are drained. The TUI disables input and shows a "Applying changes..." overlay during the `APPLYING` state. Test state transitions independently of subprocess I/O. Never apply changes while any reader coroutine or thread is still active.

### Phase

Design the state machine during the architecture phase, before implementing the apply step. It must be in place before the two features (streaming + apply) are integrated.

---

## Pitfall 11: Agent output is parsed by fragile string matching instead of structured protocol

**Category:** Integration
**Severity:** Medium

### What goes wrong

The code that decides "agent A agrees with agent B" or "this output is a code block" uses regex or keyword matching on raw CLI output. When the CLI tool changes its output format (version upgrade, locale, terminal width difference), all downstream logic silently breaks. Consensus detection fails and the debate never terminates.

### Warning signs

- Consensus logic uses `if "I agree" in line` or similar literal string checks.
- Tests for consensus pass with a hardcoded agent output fixture but fail with the real CLI.
- Upgrading the `claude` CLI version breaks the debate termination logic.
- The regex for code block extraction is duplicated in three places.

### Prevention strategy

Define a thin `AgentOutputParser` abstraction that encapsulates all output interpretation. Back it with unit tests using realistic but varied output samples. Where possible, use structured output flags (`--output-format json` if the CLI supports it) instead of parsing natural language. Version-lock the CLI tools alongside the Python dependencies and explicitly test against each locked version. Expose a `--dry-run` or replay mode that feeds recorded CLI output through the parser for regression testing.

### Phase

Define `AgentOutputParser` and its contract before integrating with the live CLI. Its fake in tests should emit the same interface as the real parser.

---

## Pitfall 12: Interactive key handling conflicts with subprocess stdin requirements

**Category:** TUI / subprocess
**Severity:** Medium

### What goes wrong

Textual (and most TUI frameworks) take exclusive ownership of the terminal's stdin for key events. Some AI CLI tools also need to read from stdin for interactive prompts (e.g., "Press enter to continue" or API key entry). These two consumers conflict. The subprocess blocks waiting for input it never receives, or the TUI never gets key events because the subprocess has stolen stdin.

### Warning signs

- The TUI freezes waiting for the subprocess after a certain point in the agent run.
- A subprocess log shows `waiting for input` or similar.
- The TUI stops responding to keyboard after the first agent call.
- `subprocess.communicate()` is used (which blocks until EOF on stdin).

### Prevention strategy

Always invoke AI CLI tools with `stdin=subprocess.DEVNULL` (or `/dev/null`). Pass all required inputs as arguments or environment variables, never via stdin. If the tool requires interactive input, it is not suitable for non-interactive subprocess use — use its SDK or API directly instead. Document this as a hard constraint in the agent integration layer. Write a test that verifies the subprocess exits cleanly with `stdin=DEVNULL` and no hanging.

### Phase

Enforce `stdin=DEVNULL` from the very first subprocess invocation in the streaming spike. Never relax this constraint without a documented justification.

---

## Summary Table

| # | Pitfall | Severity | Phase |
|---|---------|----------|-------|
| 1 | Blocking reads stall the event loop | Critical | Streaming spike |
| 2 | ANSI escape codes corrupt pane rendering | High | Before first demo |
| 3 | Subprocess stdout buffering stalls streaming | High | Streaming spike |
| 4 | Thread-unsafe shared state | High | Streaming architecture |
| 5 | TTY requirements differ on CI vs local | Medium-High | First TDD cycle |
| 6 | TUI framework version churn | Medium | Project scaffolding |
| 7 | Zombie processes on exit | High | Streaming spike |
| 8 | Unbounded scrollback causes OOM | Medium | Pane widget implementation |
| 9 | Packaging fails to include assets | Medium | Project scaffolding |
| 10 | Apply step races with streaming | High | Architecture phase |
| 11 | Fragile string parsing for consensus | Medium | Before CLI integration |
| 12 | Stdin conflict between TUI and subprocess | Medium | First subprocess invocation |
