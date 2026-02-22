# Roadmap: Agent Bureau

## Overview

The existing `disagree_v1` orchestration core (parallel execution, disagreement classification, debate prompts, session persistence) is solid and stays untouched. This milestone adds the user-facing TUI layer that makes the product real: a terminal that streams multiple AI agents side-by-side, lets the user pick a winner or watch a live debate, and applies chosen diffs only after explicit confirmation. The build order is dependency-driven: the async streaming bridge must be proven correct before TUI layout is built around it, and both must be stable before the flow-control and apply step is wired in.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Async Streaming Bridge** - Async subprocess fan-out with typed event bus; all streaming correctness proven before any TUI code exists
- [ ] **Phase 2: Static TUI Layout** - Side-by-side columnar layout with keyboard navigation, syntax highlighting, and scrollable panes validated against placeholder content
- [ ] **Phase 3: Live Streaming Integration** - Bridge wired to TUI; tokens stream into correct panes in real time; status bar and disagreement state display live
- [ ] **Phase 4: Flow Control and Code Apply** - Flow picker modal, live-debate mode, pick-winner UX, diff preview, and file-write confirmation
- [ ] **Phase 5: Agent Discovery, Config, and Packaging** - Auto-detection of CLI agents on PATH, config file for default roster, and installable `agent-bureau` entry point

## Phase Details

### Phase 1: Async Streaming Bridge
**Goal**: The bridge can fan out to N agent subprocesses concurrently, stream tokens through a typed event queue, and report errors cleanly — all proven by tests before any TUI exists
**Depends on**: Nothing (first phase)
**Requirements**: AGENT-03, AGENT-04
**Success Criteria** (what must be TRUE):
  1. A test harness can invoke the bridge with a fake `AgentRunner` and receive `TokenChunk`, `AgentDone`, and `SessionComplete` events in the correct sequence
  2. When an agent subprocess times out, the bridge emits a recoverable error event and terminates the subprocess without leaving a zombie process
  3. When an agent returns malformed output, the bridge emits an error event and the harness continues without crashing
  4. All subprocess reads are non-blocking; a slow agent does not stall a fast agent's token delivery
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Project setup: pyproject.toml update (pytest-asyncio, asyncio_mode) + tui package skeleton
- [x] 01-02-PLAN.md — TDD: event bus types + bridge implementation proven via FakeAgentRunner tests
- [x] 01-03-PLAN.md — PTY agent spike: document real claude binary streaming behavior (PTY vs PIPE)

### Phase 2: Static TUI Layout
**Goal**: Users can see the columnar agent layout, scroll panes, navigate by keyboard, and read syntax-highlighted code — all without live agents running
**Depends on**: Phase 1
**Requirements**: TUI-01, TUI-02, TUI-04, TUI-05, TUI-06, TUI-07, TUI-08
**Success Criteria** (what must be TRUE):
  1. User sees two (or more) named agent columns side-by-side, each with placeholder content, at 80-column, 120-column, and wide terminal widths
  2. User can scroll each pane independently without affecting other panes; scrollback is bounded (no OOM)
  3. Code blocks in pane content are syntax-highlighted
  4. User can navigate the entire TUI using only the keyboard (scroll up/down, switch panes, exit)
  5. User can exit at any time with Ctrl-C or `q` and the terminal is left in a clean state
**Plans**: 4 plans

Plans:
- [ ] 02-01-PLAN.md — Add textual>=0.80.0,<9 runtime dependency to pyproject.toml
- [ ] 02-02-PLAN.md — TDD: write_content_to_pane() fenced-code parser proven by tests
- [ ] 02-03-PLAN.md — AgentPane widget + QuitScreen widget + styles.tcss with Pilot tests
- [ ] 02-04-PLAN.md — AgentBureauApp wiring + integration tests + human visual checkpoint

### Phase 3: Live Streaming Integration
**Goal**: Users can watch tokens stream into the correct agent panes in real time, see the status bar reflect live agent state, and see disagreements flagged as they are classified
**Depends on**: Phase 2
**Requirements**: TUI-03, TUI-09, ORCH-02, ORCH-03, ORCH-06
**Success Criteria** (what must be TRUE):
  1. When a prompt is submitted, both agents begin streaming simultaneously and their tokens appear in the correct labeled panes as they arrive
  2. The status bar updates in real time: it shows which agents are still streaming, when all agents are done, and when a disagreement has been classified
  3. Disagreements between agents are visually indicated in the TUI (type label: approach / facts / confidence_gap)
  4. The apply step cannot begin while any agent subprocess is still running or its queue is unread; the state machine enforces this
**Plans**: TBD

### Phase 4: Flow Control and Code Apply
**Goal**: Users can choose their session flow before agents run, watch a live debate with round-by-round streaming, pick a winner, and apply that agent's proposed file changes only after reviewing a diff and confirming
**Depends on**: Phase 3
**Requirements**: ORCH-01, ORCH-04, ORCH-05, APPLY-01, APPLY-02, APPLY-03
**Success Criteria** (what must be TRUE):
  1. At the start of each session, user is presented with a flow-picker modal and can choose "pick-one" or "live-debate" before agents run
  2. In live-debate mode, user watches each round of agent exchange stream into the panes; user can end the debate at any time with a keypress
  3. When an agent proposes file changes, user sees a diff preview before any file is written
  4. User must press an explicit confirmation key before any file is written to disk; no file is ever written without this step
  5. In pick-winner flow, user can select which agent's proposed changes to apply
**Plans**: TBD

### Phase 5: Agent Discovery, Config, and Packaging
**Goal**: Agent Bureau detects installed CLI agents automatically, remembers a preferred roster via config file, and installs cleanly on macOS and Linux with a single command
**Depends on**: Phase 4
**Requirements**: AGENT-01, AGENT-02, PKG-01, PKG-02, PKG-03
**Success Criteria** (what must be TRUE):
  1. On startup, Agent Bureau scans PATH and shows the user only CLI agents that are actually installed (claude, codex, aider, etc.)
  2. User can save a preferred agent pair to a config file and have it auto-selected on next launch
  3. `pip install .` in a fresh virtualenv completes without errors on macOS and Linux with Python 3.10+
  4. After install, running `agent-bureau` in a terminal launches the TUI with no additional configuration required
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Async Streaming Bridge | 3/3 | Complete | 2026-02-22 |
| 2. Static TUI Layout | 2/4 | In Progress|  |
| 3. Live Streaming Integration | 0/TBD | Not started | - |
| 4. Flow Control and Code Apply | 0/TBD | Not started | - |
| 5. Agent Discovery, Config, and Packaging | 0/TBD | Not started | - |
