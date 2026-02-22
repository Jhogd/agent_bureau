# Plan 01-02 Summary: Async Streaming Bridge — Event Bus and FakeAgentRunner Tests

**Completed:** 2026-02-22
**Status:** All tests passing

## Event Types Implemented

### `src/tui/event_bus.py`

| Type | Fields | Notes |
|------|--------|-------|
| `AgentSpec` | `name`, `command`, `args=()` | `.build_argv(prompt)` → `[command, *args, prompt]` |
| `TokenChunk` | `agent`, `text`, `type="token"` | One streamed line from an agent |
| `AgentDone` | `agent`, `full_text`, `exit_code`, `type="done"` | Terminal event: success |
| `AgentError` | `agent`, `message`, `exit_code`, `type="error"` | Terminal event: non-zero exit |
| `AgentTimeout` | `agent`, `type="timeout"` | Terminal event: exceeded timeout |
| `BridgeEvent` | Union of above 4 event types | Type alias |

All are frozen dataclasses. `BridgeEvent = Union[TokenChunk, AgentDone, AgentError, AgentTimeout]`.

## Test Functions Written

### `tests/tui/test_bridge.py`

| Function | Covers |
|----------|--------|
| `test_both_agents_produce_tokens` | Both agents emit TokenChunk events when both succeed |
| `test_error_does_not_kill_surviving_agent` | **AGENT-04**: codex errors, claude still completes with AgentDone |
| `test_timeout_does_not_kill_surviving_agent` | **AGENT-03**: claude hangs, codex still completes with AgentDone |
| `test_terminal_events_exactly_two` | Bridge always emits exactly 2 terminal events |
| `test_done_event_contains_full_text` | AgentDone.full_text contains all streamed lines |
| `test_agent_spec_build_argv` | AgentSpec.build_argv() builds correct argument vectors |
| `test_both_error_still_two_terminal_events` | Both agents failing → 2 AgentError terminal events |

7 tests, 14 assertion lines. All pass.

## Deviations from RESEARCH.md

None. All RESEARCH.md patterns honored:
- `asyncio.Queue` as the shared bridge event bus
- `asyncio.create_task` for concurrent fan-out
- Consumer loop reads until `done_count == 2`
- `asyncio.wait_for` wraps the stream coroutine for timeout
- `FakeAgentRunner.stream_lines` raises `RuntimeError` on `exit_code != 0`

## Pitfalls Encountered

### `tests/tui/__init__.py` shadowing `src/tui/`

**Problem:** When `tests/tui/__init__.py` exists, pytest adds `tests/` to sys.path for package resolution. This causes `import tui` to resolve to `tests/tui/` instead of `src/tui/`, producing `ModuleNotFoundError: No module named 'tui.event_bus'` even though the file exists.

**Fix:** Removed `tests/tui/__init__.py`. Pytest discovers `tests/tui/test_bridge.py` correctly without it, and `pythonpath = ["src"]` in pyproject.toml ensures `src/tui/` is found.

**Lesson:** Do NOT create `__init__.py` in test subdirectories when source packages share the same name (`tui`). Test package init files cause parent-directory sys.path insertion that shadows same-named source packages.

## Commit SHAs

| Step | SHA | Message |
|------|-----|---------|
| test (RED) | `b5e08c4` | test: Add RED tests and FakeAgentRunner for async streaming bridge |
| feat (GREEN) | `d829360` | feat: Implement event bus, bridge, and PTY spike — all tests passing |
