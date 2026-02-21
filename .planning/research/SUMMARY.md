# Research Summary: Agent Bureau TUI Layer

**Synthesized:** 2026-02-21
**Milestone:** Adding a Textual TUI layer to the existing Python multi-agent orchestration core
**Research files:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---

## Executive Summary

Agent Bureau is a terminal-based multi-agent AI coding orchestration tool. The backend (parallel agent execution, disagreement classification, debate prompts, session persistence) already exists and is stable. This milestone adds a user-facing TUI layer that streams output from multiple AI CLI agents side-by-side in real time, lets users pick a winner or watch a live debate, and applies the chosen diff to disk with explicit confirmation. The product's identity is the terminal — it is a power-user CLI tool, not a GUI app, and every design decision must reinforce that.

The correct architecture is a layered one: the existing orchestration core is left completely untouched, and a new `tui/` module adds a presentation layer above it via an async bridge. The bridge — `StreamingOrchestratorBridge` — uses `asyncio.create_subprocess_exec` to fan out to N agents concurrently, streams tokens through an `asyncio.Queue`, and posts typed message events into Textual's widget event loop. Textual is the right TUI framework: it is asyncio-native, has first-class `RichLog` streaming widgets, and supports the side-by-side columnar layout required. The key invariant throughout is that the queue is the only interface between the subprocess world and the widget world.

The primary risks are all in the streaming layer: blocking reads, stdout buffering (non-TTY mode), ANSI escape code corruption, zombie subprocesses on exit, and a race between the apply-changes step and ongoing streaming. All of these must be addressed in the very first streaming spike — they are architectural decisions, not cleanup tasks. Any one of them left unresolved at the start will cascade into workarounds throughout the codebase.

---

## Key Findings

### From STACK.md

| Technology | Decision | Rationale |
|---|---|---|
| Textual `>=0.70.0,<1.0` | Adopt | Asyncio-native, RichLog streaming, Horizontal layout, ModalScreen — covers all TUI requirements out of the box |
| `asyncio.create_subprocess_exec` | Adopt | Native asyncio subprocess streaming; pairs directly with Textual's `@work` coroutines; no thread pool needed |
| `strip_ansi` / regex | Adopt | Strip ANSI codes before writing to RichLog; required — raw codes corrupt widget rendering |
| `pytest-asyncio` | Add | Required for testing async bridge and streaming code |
| `textual[dev]` | Add | Provides headless `App.run_test()` and `Pilot` API for automated TUI tests |
| Existing core (`orchestrator.py`, `adapters.py`, `classifier.py`, `adjudication.py`, `store.py`) | Keep as-is | Bridge pattern isolates TUI; no changes to tested code |

**Critical version constraint:** Pin Textual to `>=0.70.0,<1.0` and commit a lock file. Textual has frequent minor-version API changes that silently break layouts.

**PTY flag:** Some CLI agents (claude, aider) detect non-TTY stdout and disable streaming. Use `pty.openpty()` as a fallback if buffering issues appear in the streaming spike.

---

### From FEATURES.md

**Table stakes (must have before any public use):**
- Streaming output rendered token-by-token
- Agent labels identifying which pane belongs to which agent
- Scrollable output per pane
- Exit/cancel at any time (Ctrl-C, `q`) without corrupting state
- Clear error messages on agent failure or timeout
- Diff preview before applying any file changes
- Explicit user confirmation before writes
- Keyboard-driven navigation
- Syntax highlighting for code blocks
- Responsive layout at common terminal widths (80/120+)

**High-value differentiators (build in this milestone):**
- Side-by-side agent panes (core value proposition)
- Live debate view (streaming adjudication)
- Pick-winner UX with diff application
- Disagreement visualization and consensus indicator
- Flow picker (pick-one vs. live-debate) per session
- Progress indicators and status bar during agent runs

**Should-have but deferrable to v2:**
- Hunk-level accept/reject (high complexity, high value — defer until core loop is stable)
- Merge/hybrid apply (very high complexity)
- Token/cost and latency display
- Auto-run tests after apply
- Session persistence and replay/audit trail

**Anti-features — do not build:**
- GUI/Electron app
- Built-in model inference
- Automatic code application without user review
- Monolithic single-agent mode
- Persistent chat history UI
- Voice input
- IDE extension

**The product thesis:** Multiple agents disagreeing is the entire value. Any feature that reduces the multi-agent comparison or removes the human confirmation step undermines the product.

---

### From ARCHITECTURE.md

**Major components and responsibilities:**

| Component | Responsibility |
|---|---|
| `tui/bridge.py` (StreamingOrchestratorBridge) | Fans out to N agents via `asyncio.create_subprocess_exec`; reads tokens; puts typed messages on an `asyncio.Queue`; calls existing classifier/adjudication/store after streaming |
| `tui/event_bus.py` | Defines immutable dataclass message types: `TokenChunk`, `AgentDone`, `DisagreementDetected`, `AdjudicationComplete`, `SessionComplete` |
| `tui/app.py` | Textual `App` subclass; owns event loop; runs bridge as `@work` coroutine; routes queue messages into Textual message bus |
| `tui/layout.py` (AgentColumnLayout) | `Horizontal` container; dynamically mounts `AgentPanel` instances at runtime |
| `tui/panels.py` (AgentPanel) | Scrollable `RichLog` per agent; handles `TokenChunk` and `AgentDone` messages |
| `tui/status_bar.py` | Bottom bar showing session mode, disagreement state, adjudication result; handles `DisagreementDetected` and `AdjudicationComplete` |
| `tui/flow_picker.py` | `ModalScreen` for per-session pick-one vs. live-debate selection |
| `tui/discovery.py` | PATH scanning for known CLI agents; produces `AgentSpec` list at startup |

**Key patterns:**
- Queue-as-interface: the `asyncio.Queue` is the only coupling between bridge and widgets. No widget ever touches a subprocess object directly.
- One-way dependency: nothing in `tui/` imports from `orchestrator.py` et al. except `bridge.py`. Nothing in the existing core imports from `tui/`.
- Bridge Option A (preferred for milestone 1): Bridge bypasses `adapters.py` for streaming and calls `classifier`, `adjudication`, `store` directly. This keeps the TUI fully isolated. Option B (extend `AgentAdapter` with async `stream()` method) is the right long-term design and should be a planned refactor in a later milestone.
- Extension point: adding a new CLI agent is a one-line entry in `KNOWN_AGENTS` dict in `discovery.py`. No other module changes.

**Debate lifecycle state machine (critical for correctness):**
`STREAMING → CONSENSUS_REACHED → AWAITING_USER → APPLYING → DONE`

Transitions are gated. The apply step only begins after all subprocesses are terminated and their queues are drained. This is not optional — racing the apply step against streaming causes partial file writes.

---

### From PITFALLS.md

**Top pitfalls ranked by severity and build-phase relevance:**

| Pitfall | Severity | Must Address In |
|---|---|---|
| Blocking reads stall event loop | Critical | Streaming spike (Phase 1) |
| Zombie subprocesses on exit | High | Streaming spike (Phase 1) |
| Apply step races with streaming | High | Architecture design (before Phases 1+3 merge) |
| ANSI codes corrupt pane rendering | High | Before first end-to-end demo |
| Stdout buffering stalls streaming | High | Streaming spike (Phase 1) |
| Thread-unsafe shared state | High | Streaming architecture (Phase 1) |
| Stdin conflict (TUI vs subprocess) | Medium | First subprocess invocation |
| TTY/PTY requirements differ on CI | Medium-High | First TDD cycle |
| Unbounded scrollback causes OOM | Medium | Pane widget implementation |
| TUI framework version churn | Medium | Project scaffolding |
| Packaging fails to include assets | Medium | Project scaffolding |
| Fragile string parsing for consensus | Medium | Before CLI integration |

**Prevention strategies that must be baked in from day one (not deferred):**
1. Use `asyncio.create_subprocess_exec` with `await stream.readline()` — never blocking I/O in a coroutine.
2. Always set `stdin=subprocess.DEVNULL` — no exceptions.
3. Wrap all subprocess lifecycle in a context manager with `proc.terminate()` + `proc.wait()` in cleanup.
4. Strip ANSI/control sequences before writing any text to widget panes.
5. Pin Textual minor version and commit a lock file at project scaffold time.
6. Use `importlib.resources` for bundled `.tcss` assets, not `Path(__file__)` tricks.
7. Define an `AgentRunner` protocol with a fake implementation so streaming tests never need a real terminal.

---

## Implications for Roadmap

The architecture and pitfalls research align strongly on a 5-phase build order. The rationale is dependency-driven: each phase must produce independently testable artifacts before the next phase begins. This is not a arbitrary grouping — it reflects the structural constraint that bridge correctness must be proven before TUI code is written around it.

### Suggested Phase Structure

**Phase 1: Async Streaming Bridge**
- Rationale: Everything depends on this. Bridge correctness must be proven before any TUI layout work.
- Delivers: `tui/event_bus.py`, `tui/bridge.py`, `tui/discovery.py`; async subprocess fan-out tested via plain `asyncio.run()` harness; no TUI required.
- Features enabled: None visible yet, but all streaming features depend on this.
- Pitfalls to address: #1 (blocking reads), #3 (buffering), #4 (thread safety), #7 (zombie processes), #12 (stdin conflict)
- Testing: Pure asyncio unit tests, no Textual dependency. `AgentRunner` fake implementation introduced here.
- Research flag: None — patterns are well-documented. Spike on PTY buffering with real `claude` CLI invocation required.

**Phase 2: Static TUI Layout**
- Rationale: Layout bugs are easier to diagnose with placeholder content than with live streaming data.
- Delivers: `tui/panels.py`, `tui/layout.py`, `tui/status_bar.py`, `tui/app.py` (stub, no bridge); layout validated at 80/120/wide terminals.
- Features enabled: Agent labels, scrollable panes, keyboard navigation, syntax highlighting, responsive layout (all table stakes).
- Pitfalls to address: #6 (version churn — pin Textual), #9 (packaging scaffold — entry point and assets before any TUI code), #8 (unbounded scrollback — set `max_lines` during widget construction)
- Testing: Textual `Pilot` headless snapshot tests.
- Research flag: None — standard Textual patterns.

**Phase 3: Wire Bridge to TUI**
- Rationale: Both bridge (Phase 1) and layout (Phase 2) are verified independently before connecting them. The connection is a single integration point.
- Delivers: `tui/app.py` updated with bridge worker; `tui/panels.py` message handlers (`on_token_chunk`, `on_agent_done`); `tui/status_bar.py` handlers (`on_disagreement_detected`, `on_adjudication_complete`); live streaming visible in correct panes.
- Features enabled: Streaming output, progress indicators, per-agent status, disagreement state display.
- Pitfalls to address: #2 (ANSI stripping — must be in place before first live demo), #10 (apply-races-streaming — state machine must be designed before implementing the apply step in Phase 4)
- Testing: Combined asyncio + Textual `Pilot` tests with fake `AgentRunner`.
- Research flag: None — standard Textual worker pattern.

**Phase 4: Flow Picker, Apply Step, and Diff UX**
- Rationale: Requires the full streaming pipeline. Flow mode changes only bridge adjudication behavior. Apply step requires the state machine from Phase 3.
- Delivers: `tui/flow_picker.py` (modal); bridge updated for `LIVE_DEBATE` mode (streaming adjudication); pick-winner UX; diff preview; file writer with dry-run flag; user confirmation before writes.
- Features enabled: Flow selection, live debate view, pick-winner, diff preview, confirmation prompt, dry-run mode. Optional: git commit after apply.
- Pitfalls to address: #10 (apply step state machine must gate the APPLYING transition on all subprocesses terminated and queues drained)
- Testing: State machine unit tests independent of subprocess I/O; apply step tested with dry-run mode.
- Research flag: Consider `/gsd:research-phase` for hunk-level accept/reject if planned — it is High complexity and requires a diff parser design decision.

**Phase 5: CLI Integration, Agent Discovery, and Packaging**
- Rationale: All internal components must be stable before wiring real subprocess invocations. External agent CLI behavior is the hardest thing to control in tests.
- Delivers: `cli.py` updated with `--tui` flag; `tui/discovery.py` wired into `tui/app.py` startup; system test with real `claude` and `aider` invocations; `pip install` CI validation.
- Features enabled: `disagree --tui` entry point; auto-discovery of installed CLI agents; config file for default agent roster.
- Pitfalls to address: #5 (TTY/PTY on CI), #9 (packaging validation: fresh venv install test), #11 (AgentOutputParser abstraction for structured vs. natural-language output)
- Testing: System tests with real CLI invocations; packaging CI gate: `pip install dist/*.whl && agent-bureau --version`.
- Research flag: None — well-understood integration patterns.

**Deferred (v2+ milestone):**
- Hunk-level accept/reject (High complexity)
- Merge/hybrid apply (Very high complexity)
- Token/cost and latency display (Medium complexity, medium value)
- Session persistence and replay (Medium complexity, nice-to-have)
- Auto-run tests after apply
- Adapter refactor: Option B (extend `AgentAdapter` with async `stream()` method) — correct long-term design, plan as a Phase 6 refactor after TUI stabilizes.

---

## Confidence Assessment

| Area | Confidence | Notes |
|---|---|---|
| Stack | High | Textual is the clear choice; asyncio subprocess streaming is stdlib; all decisions are well-evidenced with specific version numbers and code patterns |
| Features | High | Survey of 6+ tools (aider, Claude Code, Cursor, Continue.dev, CrewAI, AutoGen, OpenHands) gives strong signal on what table stakes are and where the differentiation lives |
| Architecture | High | Component boundaries are explicit, dependency directions are strict, code skeletons are provided; bridge pattern is well-understood in async Python |
| Pitfalls | High | 12 pitfalls documented with specific warning signs and prevention strategies; all are grounded in known failure modes of asyncio subprocess streaming and TUI framework work |

**Overall confidence: HIGH**

**Gaps requiring attention during planning:**

1. **PTY buffering per agent CLI** — Which CLI tools require PTY mode to stream properly (aider vs. claude vs. others) needs a real spike with each tool. Document per-agent behavior in `KNOWN_AGENTS`.

2. **AgentOutputParser scope** — The existing `classifier.py` uses some form of output interpretation. Whether it can be reused as the `AgentOutputParser` abstraction or needs wrapping is not clear from the research. Examine `classifier.py` source before Phase 5.

3. **Hunk-level accept/reject design** — If this is targeted for this milestone, it needs its own architecture spike. The diff parser format and hunk selection UI are non-trivial. Current recommendation: defer to v2.

4. **CI environment for TUI tests** — Headless Textual testing via `Pilot` works, but the TTY-dependent real subprocess tests (Phase 5) need a defined CI environment. Determine whether GitHub Actions provides a pseudo-terminal before Phase 5.

---

## Sources (Aggregated)

- Textual documentation and API reference (textualize.io), as of August 2025
- `asyncio` Python stdlib documentation — `create_subprocess_exec`, `StreamReader`, `Queue`
- aider documentation and changelog (aider.chat)
- Cursor documentation (cursor.com/docs)
- Continue.dev documentation (continue.dev/docs)
- Claude Code release notes and help text
- AutoGen/Microsoft multi-agent research papers
- CrewAI documentation
- OpenHands/OpenDevin project README
- LangGraph documentation
- General patterns from multi-pane terminal tools: lazygit, k9s, atuin
- Existing source structure at `/Users/jakeogden/agent-bureau/src/disagree_v1/`

---

*Research synthesized by gsd-synthesizer — 2026-02-21*
