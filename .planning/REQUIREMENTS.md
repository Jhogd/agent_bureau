# Requirements: Agent Bureau

**Defined:** 2026-02-21
**Core Value:** A developer can send a coding prompt, see how multiple AI agents approach it differently, and decide — in the moment — whether to pick a winner or watch them debate before touching any code.

## v1 Requirements

### TUI Layout

- [x] **TUI-01**: User sees agent responses displayed side-by-side in columnar panes, one column per agent
- [x] **TUI-02**: Each pane is labeled with the agent's name (e.g., "claude", "codex")
- [ ] **TUI-03**: Agent output streams token-by-token into the correct pane as the agent responds
- [x] **TUI-04**: Each pane is independently scrollable with bounded scrollback (no OOM)
- [x] **TUI-05**: Code blocks in agent output are syntax-highlighted
- [x] **TUI-06**: Layout adapts to terminal width (80 / 120 / wide column breakpoints)
- [ ] **TUI-07**: User can navigate the TUI entirely by keyboard (scroll, pick, exit)
- [ ] **TUI-08**: User can exit at any time with Ctrl-C or q without corrupting state or leaving zombie processes
- [ ] **TUI-09**: Status bar shows current session mode, agent streaming state, and adjudication status

### Multi-Agent Orchestration

- [ ] **ORCH-01**: User is prompted at the start of each session to choose a flow: pick-one or live-debate
- [ ] **ORCH-02**: Both agents run in parallel from the moment the prompt is submitted
- [ ] **ORCH-03**: Disagreements between agents are visualized in the TUI (approach, facts, confidence gap)
- [ ] **ORCH-04**: In live-debate mode, user watches each round of agent exchange stream in real time
- [ ] **ORCH-05**: In live-debate mode, user controls when to end the debate (keypress)
- [ ] **ORCH-06**: State machine gates all transitions — streaming completes before any apply step begins

### Code Application

- [ ] **APPLY-01**: When an agent proposes file changes, user sees a diff preview before anything is written
- [ ] **APPLY-02**: User must explicitly confirm (keypress) before any file is written to disk
- [ ] **APPLY-03**: User can pick which agent's proposed changes to apply (pick-winner flow)

### Agent Discovery & Config

- [ ] **AGENT-01**: At startup, Agent Bureau auto-detects installed CLI agents on PATH (claude, codex, aider, etc.)
- [ ] **AGENT-02**: User can save a preferred agent pair/roster to a config file for reuse
- [x] **AGENT-03**: If an agent times out, user sees a clear error message and the session recovers gracefully
- [x] **AGENT-04**: If an agent returns malformed output, user sees a clear error and the session does not crash

### Packaging & Install

- [ ] **PKG-01**: User can install Agent Bureau with a single pip command (`pip install .`)
- [ ] **PKG-02**: After install, user can start Agent Bureau with a single terminal command (`agent-bureau`)
- [ ] **PKG-03**: Works on macOS and Linux with Python 3.10+

## v2 Requirements

### Code Application

- **APPLY-04**: Dry-run mode — preview diffs without writing to disk
- **APPLY-05**: Hunk-level accept/reject — apply only selected sections of a diff
- **APPLY-06**: Hybrid merge — apply a hand-composed combination of both agents' changes
- **APPLY-07**: Auto-run tests after applying changes

### Observability

- **OBS-01**: Per-agent token count and cost display
- **OBS-02**: Per-agent response latency display
- **OBS-03**: Session replay — browse past sessions from the JSONL store

### Agent Protocol

- **AGENT-05**: Formal `AgentAdapter` async `stream()` protocol (replace bridge bypass)

## Out of Scope

| Feature | Reason |
|---------|--------|
| GUI / Electron / web interface | Terminal-first, always |
| Built-in model inference | Subprocess-based execution only; no direct API calls |
| Automatic code apply without user review | Core safety requirement — human in the loop always |
| Persistent chat history UI | Each prompt is a fresh session for v1 |
| IDE / editor extension | Web-first would come before IDE, both are out of scope |
| Voice input | Out of scope for CLI tool |
| Windows support | Unix-first; Windows compatibility is a v2+ concern |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TUI-01 | Phase 2 | Complete |
| TUI-02 | Phase 2 | Complete |
| TUI-03 | Phase 3 | Pending |
| TUI-04 | Phase 2 | Complete |
| TUI-05 | Phase 2 | Complete |
| TUI-06 | Phase 2 | Complete |
| TUI-07 | Phase 2 | Pending |
| TUI-08 | Phase 2 | Pending |
| TUI-09 | Phase 3 | Pending |
| ORCH-01 | Phase 4 | Pending |
| ORCH-02 | Phase 3 | Pending |
| ORCH-03 | Phase 3 | Pending |
| ORCH-04 | Phase 4 | Pending |
| ORCH-05 | Phase 4 | Pending |
| ORCH-06 | Phase 3 | Pending |
| APPLY-01 | Phase 4 | Pending |
| APPLY-02 | Phase 4 | Pending |
| APPLY-03 | Phase 4 | Pending |
| AGENT-01 | Phase 5 | Pending |
| AGENT-02 | Phase 5 | Pending |
| AGENT-03 | Phase 1 | Complete |
| AGENT-04 | Phase 1 | Complete |
| PKG-01 | Phase 5 | Pending |
| PKG-02 | Phase 5 | Pending |
| PKG-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after roadmap creation*
