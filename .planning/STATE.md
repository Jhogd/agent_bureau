# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** A developer can send a coding prompt, see how multiple AI agents approach it differently, and decide — in the moment — whether to pick a winner or watch them debate before touching any code.
**Current focus:** Phase 1 — Async Streaming Bridge

## Current Position

Phase: 1 of 5 (Async Streaming Bridge)
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2026-02-22 — Plan 01-01 complete: tui package skeleton and pytest-asyncio configured

Progress: [█░░░░░░░░░] 7%

## Performance Metrics

**Velocity:**
- Total plans completed: 1
- Average duration: 2 min
- Total execution time: 0.03 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-async-streaming-bridge | 1/3 | 2 min | 2 min |

**Recent Trend:**
- Last 5 plans: 01-01 (2 min)
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Build on disagree_v1 foundation — core is untouched; bridge pattern isolates TUI from existing orchestration
- [Roadmap]: Textual chosen as TUI framework (asyncio-native, RichLog streaming, ModalScreen); pin >=0.70.0,<1.0 with lock file
- [Roadmap]: Bridge bypasses adapters.py for streaming in Phase 1 (Option A); Option B async stream() refactor is v2
- [01-01]: Project renamed from disagree-v1 to agent-bureau in pyproject.toml per research recommendation
- [01-01]: pytest-asyncio pinned >=0.25,<2.0 to control major version and avoid v2 breaking changes
- [01-01]: asyncio_mode=auto configured — all async def test_* functions run without @pytest.mark.asyncio decorators

### Pending Todos

None yet.

### Blockers/Concerns

- PTY buffering: some CLI agents (aider, claude) detect non-TTY stdout and disable streaming — needs a real spike per agent in Phase 1
- AgentOutputParser scope: whether classifier.py can be reused as the output parsing abstraction is unclear; examine before Phase 5
- CI environment for TUI tests: headless Pilot works but real subprocess tests in Phase 5 require a pseudo-terminal in CI

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed 01-async-streaming-bridge/01-01-PLAN.md
Resume file: None
