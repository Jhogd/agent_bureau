# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** A developer can send a coding prompt, see how multiple AI agents approach it differently, and decide — in the moment — whether to pick a winner or watch them debate before touching any code.
**Current focus:** Phase 4 — Flow Control and Code Apply

## Current Position

Phase: 4 of 5 (Flow Control and Code Apply — not started)
Plan: 0 of TBD in current phase
Status: Phase 3 complete — all 4 plans executed and human-verified; ready for Phase 4
Last activity: 2026-02-23 — 03-04: AgentBureauApp fully wired; human visual checkpoint approved; Phase 3 complete

Progress: [████████░░] 80%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: ~10 min per plan (including parallel Wave 2)
- Total execution time: ~2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-async-streaming-bridge | 3/3 | ~1 hr | ~20 min |

**Recent Trend:**
- Last 3 plans: 03-02, 03-03, 03-04 (all complete)
- Trend: Phase 3 complete

*Updated after each plan completion*

| Phase 02-static-tui-layout P01 | 2 min | 1 task | 1 file |
| Phase 02-static-tui-layout P02 | 3 min | 2 tasks | 2 files |
| Phase 02-static-tui-layout P03 | 3 min | 2 tasks | 6 files |
| Phase 02-static-tui-layout P04 | 15 | 2 tasks | 3 files |
| Phase 03-live-streaming-integration P01 | 5 min | 2 tasks | 4 files |
| Phase 03-live-streaming-integration P03 | 6 | 2 tasks | 4 files |
| Phase 03-live-streaming-integration P04 | 15 | 2 tasks | 2 files |

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
- [Phase 02-01]: Pin textual>=0.80.0,<9 (not >=0.70.0,<1.0) — textual is at major version 8.x; <1.0 upper bound would have failed
- [Phase 02-01]: Use project .venv at /agent-bureau/.venv — system pip is externally managed (PEP 668)
- [Phase 02-02]: MagicMock used as RichLog stand-in — avoids async Pilot context, keeps tests fast and synchronous
- [Phase 02-02]: tests/tui/__init__.py intentionally absent — prevents src/tui/ shadowing in pytest sys.path (Phase 01-02 pitfall)
- [Phase 02-02]: SCROLLBACK_LIMIT=5000 defined as module constant for future RichLog max_lines configuration
- [Phase 02-03]: str(label.render()) used instead of label.renderable — Textual 8.x Label API change
- [Phase 02-03]: app.screen.query_one() required for modal widget queries — app.query_one() searches default screen only
- [Phase 02-03]: QuitScreen.DEFAULT_CSS duplicates styles.tcss dialog rules for standalone portability
- [Phase 02-static-tui-layout]: No up/down bindings at App level — AgentPane handles scroll independently to avoid cross-pane scrolling
- [Phase 02-static-tui-layout]: ctrl+c uses priority=True to intercept before Textual built-in quit and show QuitScreen dialog
- [02-04]: Dialog padding set to 1 4 and buttons to width: 100% — human visual review flagged left-aligned Quit/Cancel buttons; fix confirmed by user
- [03-01]: @dataclass decorator applied to Message subclasses — clean field declaration, matches plan spec exactly
- [03-01]: BridgeEvent union type annotated on AgentFinished.event — explicit typed link between bridge and TUI layers
- [03-01]: tests/tui/__init__.py intentionally absent — prevents src/tui/ shadowing in pytest sys.path (Phase 01-02 pitfall confirmed again)
- [Phase 03-03]: StatusBar uses Static.update() for state-driven text changes — no Textual reactive needed; explicit call from AgentBureauApp
- [Phase 03-03]: PromptBar is layout-only; Input.Submitted handling intentionally left to AgentBureauApp (SRP)
- [Phase 03-03]: Phase 3 CSS rules appended to styles.tcss without modifying existing rules (OCP compliance)
- [03-04]: _run_session uses post_message() exclusively — no direct widget calls from async worker (thread safety per RESEARCH.md)
- [03-04]: Classification gated strictly on len(_terminal_events) == 2 — no race condition possible
- [03-04]: CommandJsonAdapter reused for TUI-side JSON parsing; try/except yields empty disagreements on non-JSON output
- [03-04]: watch_session_state() guards with try/except for early lifecycle safety before Input is mounted
- [03-04]: Human visual verification approved — status bar, prompt bar, prompt input, agent panes, and layout all confirmed correct

### Pending Todos

None.

### Blockers/Concerns

- PTY buffering: claude CLI was blocked by nested session detection during spike; actual PTY vs PIPE streaming behavior for real prompts remains unverified. Phase 3 integration tests should run outside Claude Code with CLAUDECODE unset. Items 6-12 of visual checklist (streaming tokens, status updates, classification) need manual verification outside Claude Code before Phase 5.
- AgentOutputParser scope: whether classifier.py can be reused as the output parsing abstraction is unclear; examine before Phase 5
- CI environment for TUI tests: headless Pilot works but real subprocess tests in Phase 5 require a pseudo-terminal in CI

## Session Continuity

Last session: 2026-02-23
Stopped at: Completed 03-04-PLAN.md — Phase 3 complete
Resume file: None
