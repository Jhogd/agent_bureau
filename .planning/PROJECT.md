# Agent Bureau

## What This Is

Agent Bureau is a terminal-based multi-agent coding interface that runs multiple AI CLI agents (Claude, Codex, and others) simultaneously against the same prompt. It displays their responses side-by-side in a TUI, lets the user watch them debate live, and gives the user per-session control over whether to pick one answer, watch a live deliberation, or apply a code change only after agents agree.

## Core Value

A developer should be able to send a coding prompt, see how multiple AI agents approach it differently, and decide — in the moment — whether to pick a winner or watch them work it out together before touching any code.

## Requirements

### Validated

- ✓ Parallel agent execution (ThreadPoolExecutor fan-out) — existing
- ✓ Disagreement classification (approach, fact, confidence_gap) — existing
- ✓ Debate and reconcile follow-up prompts — existing
- ✓ JSONL session persistence — existing
- ✓ Interactive launcher (basic CLI) — existing
- ✓ Extensible adapter protocol (AgentAdapter) — existing

### Active

- [ ] Side-by-side TUI layout with columnar agent responses
- [ ] Live debate mode: user watches rounds stream in real time, decides when to stop
- [ ] Per-session flow choice: pick one OR trigger debate (decided at response time)
- [ ] Extensible agent discovery: detect any CLI agent on PATH
- [ ] Rename package to agent_bureau with clean install path
- [ ] Code change integration: when an agent proposes file edits, user picks which agent's change to apply (or waits for agreed-upon change after debate)
- [ ] Polished install experience: someone else can install and use it without docs

### Out of Scope

- Web or GUI interface — terminal-first, always
- API-only agents (no CLI) — subprocess-based execution only for v1
- Automated agent agreement (no auto-apply without user confirmation)
- Persistent cross-session memory between prompts

## Context

The project already has a working `disagree_v1` Python package at `src/disagree_v1/`. The core orchestration, adapter, classifier, adjudication, and session store layers are solid. The main gap is the user-facing TUI and the live debate streaming experience. The existing `launcher.py` is a print-based interactive loop — it works but doesn't scale to side-by-side display or real-time streaming output.

Key existing files:
- `src/disagree_v1/orchestrator.py` — core fan-out/fan-in
- `src/disagree_v1/adapters.py` — AgentAdapter protocol + CommandJsonAdapter
- `src/disagree_v1/classifier.py` — disagreement classification
- `src/disagree_v1/adjudication.py` — debate/reconcile prompt building
- `src/disagree_v1/launcher.py` — current interactive loop (to be replaced by TUI)
- `src/disagree_v1/models.py` — frozen dataclasses (AgentResponse, SessionResult)

Known concerns from codebase audit: JSON extraction brittle in CommandJsonAdapter, no logging, launcher violates SRP, subprocess timeout not configurable.

## Constraints

- **Tech stack**: Python 3.10+ with stdlib only for core (no mandatory third-party deps except optional TUI library)
- **Execution model**: All agents invoked via subprocess — no direct API calls in v1
- **Install target**: pip-installable, single command to start (`agent-bureau` or similar)
- **Platform**: Unix-first (macOS/Linux); Windows not a priority

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build on disagree_v1 foundation | Core orchestration already works and is tested | — Pending |
| Rename to agent_bureau | Folder name, cleaner brand, less combative framing | — Pending |
| TUI library choice | Textual vs Rich vs curses — tradeoffs in complexity vs capability | — Pending |
| Live debate streaming | Agents run round-by-round with user controlling cadence | — Pending |

---
*Last updated: 2026-02-21 after initialization*
