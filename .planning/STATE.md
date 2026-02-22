# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** A developer can send a coding prompt, see how multiple AI agents approach it differently, and decide — in the moment — whether to pick a winner or watch them debate before touching any code.
**Current focus:** Phase 2 — Static TUI Layout

## Current Position

Phase: 2 of 5 (Static TUI Layout — not yet started)
Plan: 0 of TBD in current phase
Status: Phase 1 complete — ready to plan Phase 2
Last activity: 2026-02-22 — Phase 1 complete: async streaming bridge verified

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: ~15 min per plan (including parallel Wave 2)
- Total execution time: ~1 hour

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-async-streaming-bridge | 3/3 | ~1 hr | ~20 min |

**Recent Trend:**
- Last 3 plans: 01-01, 01-02, 01-03 (all complete)
- Trend: Wave 2 executed in parallel

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Build on disagree_v1 foundation — core is untouched; bridge pattern isolates TUI from existing orchestration
- [Roadmap]: Textual chosen as TUI framework (asyncio-native, RichLog streaming, ModalScreen); pin >=0.70.0,<1.0 with lock file
- [Roadmap]: Bridge bypasses adapters.py for streaming in Phase 1 (Option A); Option B async stream() refactor is v2
- [01-01]: Project renamed from disagree-v1 to agent-bureau in pyproject.toml per research recommendation
- [01-01]: pytest-asyncio pinned >=0.25,<2.0; asyncio_mode=auto configured
- [01-02]: tests/tui/__init__.py must NOT exist — its presence causes tests/tui/ to shadow src/tui/ in pytest's sys.path resolution
- [01-02]: run_bridge_with_fakes() defined in test file (not in src); FakeAgentRunner is test-only infrastructure
- [01-03]: claude CLI refuses to run inside another Claude Code session (CLAUDECODE env var); Phase 3 integration tests must run outside Claude Code

### Pending Todos

None.

### Blockers/Concerns

- PTY buffering: claude CLI was blocked by nested session detection during spike; actual PTY vs PIPE streaming behavior for real prompts remains unverified. Phase 3 integration tests should run outside Claude Code with CLAUDECODE unset.
- AgentOutputParser scope: whether classifier.py can be reused as the output parsing abstraction is unclear; examine before Phase 5
- CI environment for TUI tests: headless Pilot works but real subprocess tests in Phase 5 require a pseudo-terminal in CI

## Session Continuity

Last session: 2026-02-22
Stopped at: Phase 1 complete — all 3 plans executed, verified, committed
Resume file: None
