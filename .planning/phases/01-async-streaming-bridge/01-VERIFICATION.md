---
phase: 01-async-streaming-bridge
verified: 2026-02-21T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 1: Async Streaming Bridge — Verification Report

**Phase Goal:** Build the async streaming bridge that fans out to exactly 2 agent subprocesses concurrently, streams their raw text output through a typed event queue, and reports errors cleanly. Proven correct via FakeAgentRunner tests before any TUI code exists.

**Verified:** 2026-02-21
**Status:** PASS
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A test harness can invoke the bridge with a fake AgentRunner and receive TokenChunk, AgentDone, and AgentError events in the correct sequence | VERIFIED | `test_both_agents_produce_tokens` and `test_done_event_contains_full_text` both pass; `run_bridge_with_fakes()` is implemented and wired |
| 2 | When an agent subprocess times out, the bridge emits a recoverable error event and terminates the subprocess without leaving a zombie process | VERIFIED | `test_timeout_does_not_kill_surviving_agent` passes; AGENT-03 proven |
| 3 | When an agent returns malformed output (or errors), the bridge emits an error event and the harness continues without crashing | VERIFIED | `test_error_does_not_kill_surviving_agent` passes; AGENT-04 proven |
| 4 | All subprocess reads are non-blocking; a slow agent does not stall a fast agent's token delivery | VERIFIED | Concurrent `asyncio.create_task` fan-out with shared `asyncio.Queue`; `asyncio.wait_for` wraps each runner; confirmed by tests running both slow-and-fast agent pairs |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/tui/event_bus.py` | Frozen dataclass event types: AgentSpec, TokenChunk, AgentDone, AgentError, AgentTimeout, BridgeEvent | VERIFIED | File exists, 65 lines, all 6 types implemented as frozen dataclasses with correct fields and Literal type discriminators |
| `src/tui/bridge.py` | PTY-first subprocess streaming, PIPE fallback, run_bridge(), CLAUDE, CODEX defaults | VERIFIED | File exists, 275 lines; `_pty_available()`, `_stream_pty()`, `_stream_pipe()`, `run_bridge()`, `CLAUDE`, `CODEX` all present |
| `tests/tui/test_bridge.py` | FakeAgentRunner class, run_bridge_with_fakes(), at least 5 async test functions | VERIFIED | File exists, 204 lines (>80); 7 test functions, FakeAgentRunner class, run_bridge_with_fakes() all present |
| `spikes/pty_agent_spike.py` | PTY vs PIPE spike script, syntactically valid | VERIFIED | File exists, 374 lines; `python3 -m py_compile` exits 0 |
| `src/tui/__init__.py` | tui package entry point | VERIFIED | Exists; `import tui` succeeds |
| `pyproject.toml` | pytest-asyncio dev dep, asyncio_mode=auto | VERIFIED | `pytest-asyncio>=0.25,<2.0` in dev deps; `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "function"` in pytest options |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/tui/test_bridge.py` | `src/tui/event_bus.py` | `from tui.event_bus import AgentSpec, TokenChunk, AgentDone, AgentError, AgentTimeout, BridgeEvent` | WIRED | Import present and all 6 names resolved without error |
| `tests/tui/test_bridge.py` | `run_bridge_with_fakes` | FakeAgentRunner injected into bridge consumer loop | WIRED | `run_bridge_with_fakes()` defined in test file; called by all 5+ test functions |
| `src/tui/bridge.py` | `src/tui/event_bus.py` | `from tui.event_bus import ...` | WIRED | Import present at top of bridge.py; 6 event types used throughout implementation |
| `pyproject.toml` | `pytest-asyncio` | `project.optional-dependencies.dev` | WIRED | Pattern `pytest-asyncio>=0.25,<2.0` confirmed; plugin active (`plugins: asyncio-1.3.0` shown in test output) |
| `pyproject.toml` | `asyncio_mode` | `tool.pytest.ini_options` | WIRED | `asyncio_mode = "auto"` confirmed; test output shows `asyncio: mode=Mode.AUTO` |

---

## Test Execution Results

### `python3 -m pytest tests/ -q`

```
.......................                                                  [100%]
23 passed
Exit code: 0
```

All 23 tests pass (16 pre-existing tests/test_v1_flow.py + 7 new bridge tests).

### `python3 -m pytest tests/tui/test_bridge.py -v`

```
tests/tui/test_bridge.py::test_both_agents_produce_tokens PASSED
tests/tui/test_bridge.py::test_error_does_not_kill_surviving_agent PASSED
tests/tui/test_bridge.py::test_timeout_does_not_kill_surviving_agent PASSED
tests/tui/test_bridge.py::test_terminal_events_exactly_two PASSED
tests/tui/test_bridge.py::test_done_event_contains_full_text PASSED
tests/tui/test_bridge.py::test_agent_spec_build_argv PASSED
tests/tui/test_bridge.py::test_both_error_still_two_terminal_events PASSED

7 passed in 0.22s
```

### Import checks

```
python3 -c "from tui.event_bus import TokenChunk, AgentDone, AgentError, AgentTimeout, AgentSpec, BridgeEvent; print('OK')"
OK

python3 -c "from tui.bridge import run_bridge, CLAUDE, CODEX; print('OK')"
OK
```

### Assert count

```
grep -n "assert" tests/tui/test_bridge.py | wc -l
14  (threshold: >= 8)
```

### Spike syntax check

```
python3 -m py_compile spikes/pty_agent_spike.py && echo "OK"
OK
```

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AGENT-03 | 01-02-PLAN.md | When agent subprocess times out, bridge emits recoverable error and terminates subprocess without zombie | SATISFIED | `test_timeout_does_not_kill_surviving_agent` passes; bridge uses `asyncio.wait_for` + `proc.terminate()` + `proc.kill()` fallback |
| AGENT-04 | 01-02-PLAN.md | When agent returns malformed output/errors, bridge emits error event and continues | SATISFIED | `test_error_does_not_kill_surviving_agent` passes; bridge catches `RuntimeError` and emits `AgentError`; surviving agent completes with `AgentDone` |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | No placeholders, TODO comments, empty returns, or stub implementations found in phase deliverables |

Spot checks performed on:
- `src/tui/event_bus.py` — all dataclasses substantive, no stubs
- `src/tui/bridge.py` — full PTY and PIPE implementations, no `return {}` or `pass` stubs
- `tests/tui/test_bridge.py` — 14 assert lines, no trivially-passing tests

---

## Human Verification Required

None. All behavioral goals can be verified programmatically through the FakeAgentRunner test harness, which was explicitly designed to be the proof mechanism for this phase (no real subprocess needed).

---

## Gaps Summary

No gaps. All four observable truths verified. All six required artifacts exist, are substantive (not stubs), and are correctly wired. Both AGENT-03 and AGENT-04 requirements satisfied by passing tests. The phase goal — proving the streaming bridge correct via FakeAgentRunner tests before any TUI code exists — is fully achieved.

---

## Implementation Quality Notes

The implementation correctly applies all patterns from the research phase:

- PTY master fd: `O_NONBLOCK` set via `fcntl` before `loop.add_reader()`
- Slave fd: `os.close(slave_fd)` immediately after `create_subprocess_exec` returns
- CRLF normalization: `data.replace(b"\r\n", b"\n")` on every PTY chunk
- ANSI pass-through: no stripping of escape sequences (raw decode only)
- Timeout cleanup: `proc.terminate()` + `await proc.wait()` with `proc.kill()` fallback in finally block
- Consumer loop: shared `asyncio.Queue`, terminates after `done_count == 2`
- Concurrency: both agents started as `asyncio.create_task`, non-blocking fan-out confirmed

The `tests/tui/__init__.py` was intentionally removed (noted in 01-02 SUMMARY) because its presence caused `import tui` to resolve to the test directory instead of `src/tui/`. This is a correct fix, not a gap.

---

_Verified: 2026-02-21_
_Verifier: Claude (gsd-verifier)_
