# Architecture Research — TUI Layer for Multi-Agent CLI Orchestration

**Research type:** Project Research — Architecture dimension
**Milestone:** Adding a TUI layer to existing Python orchestration code
**Date:** 2026-02-21
**Status:** Complete

---

## Question

How are multi-agent CLI tools with TUI interfaces typically structured? What are the major components, how does streaming output work, and how do you integrate a TUI framework with existing subprocess-based agent execution?

---

## Summary

Multi-agent CLI tools with TUI interfaces follow a layered architecture: a thin presentation layer (the TUI) sits above an event bus or message-passing layer, which sits above the existing orchestration and agent execution layer. The key insight is that the orchestrator must never be modified to know about the TUI. Instead, the orchestrator emits events (tokens, status changes, errors) through an async queue or callback protocol, and the TUI consumes those events reactively. Streaming subprocess output is routed through `asyncio` infrastructure using `asyncio.create_subprocess_exec` with `PIPE` on stdout/stderr, read line-by-line or chunk-by-chunk, and each chunk is posted as a message to the TUI event loop.

---

## Component Map

### Existing components (must not be structurally broken)

```
cli.py                  Entry point; parses args; kicks off a session
launcher.py / launch.py Agent discovery and launch coordination
orchestrator.py         Fan-out/fan-in; drives the session lifecycle
adapters.py             AgentAdapter protocol; subprocess invocation per agent
classifier.py           Disagreement detection between agent responses
adjudication.py         Debate/reconcile logic when disagreement is found
store.py                JSONL session persistence
models.py               Shared data models (prompts, responses, sessions)
presets.py              Pre-configured agent sets
```

### New components to introduce

```
tui/app.py              Textual App subclass; root of the widget tree; owns the event loop
tui/layout.py           AgentColumnLayout widget; renders N side-by-side agent panels
tui/panels.py           AgentPanel widget; scrollable RichLog per agent; header with status
tui/status_bar.py       Bottom bar: session mode, flow choice, adjudication state
tui/flow_picker.py      Modal screen or inline widget for per-session flow selection
tui/event_bus.py        Typed message dataclasses (TokenChunk, AgentDone, DisagreementDetected, AdjudicationComplete)
tui/bridge.py           StreamingOrchestratorBridge; adapts existing orchestrator into async generator of events; owns asyncio.Queue
tui/discovery.py        AgentDiscovery; scans PATH for known CLI patterns; returns AgentSpec list
```

---

## Component Boundaries

### What talks to what (strict dependency directions)

```
tui/app.py
  -> tui/layout.py
  -> tui/flow_picker.py
  -> tui/status_bar.py
  -> tui/bridge.py          (posts messages from bridge queue into Textual message loop)

tui/bridge.py
  -> orchestrator.py        (calls existing public interface only)
  -> tui/event_bus.py       (produces typed messages)

tui/layout.py
  -> tui/panels.py

tui/panels.py
  -> tui/event_bus.py       (consumes TokenChunk, AgentDone messages)

tui/discovery.py
  -> (stdlib only: shutil.which, os.environ["PATH"])
  -> presets.py             (merges discovered agents with preset definitions)

cli.py (updated)
  -> tui/app.py             (when --tui flag present)
  -> orchestrator.py        (existing path, unchanged for non-TUI runs)
```

**Boundary rule:** Nothing in `tui/` imports from `tui/bridge.py` except `tui/app.py`. Nothing in `orchestrator.py`, `adapters.py`, `classifier.py`, or `adjudication.py` imports anything from `tui/`. The orchestrator layer is completely unaware of the TUI.

---

## Data Flow — Streaming Output

### Current (non-TUI) flow

```
cli.py
  -> orchestrator.run_session(prompt, agents)
       -> [fan-out] adapters.invoke(agent, prompt)  [subprocess, blocks per agent]
       -> [fan-in]  collect all AgentResponse objects
       -> classifier.classify(responses)
       -> adjudication.run(responses) if disagreement
       -> store.append(session)
  -> print final output to stdout
```

### New (TUI) flow — streaming

```
cli.py  [--tui flag]
  -> tui/app.py.run()
       -> flow_picker screen (user picks: "pick one" or "live debate")
       -> bridge.start_session(prompt, agents, flow_mode)

bridge.py
  -> asyncio.create_subprocess_exec(agent_cmd, ...)
       stdout=asyncio.subprocess.PIPE
       stderr=asyncio.subprocess.PIPE
  -> per-agent reader coroutine:
       while chunk := await proc.stdout.read(256):
           await queue.put(TokenChunk(agent_id=..., text=chunk))
  -> when all readers done:
       await queue.put(AgentDone(agent_id=..., full_text=...))
  -> calls classifier.classify(collected_responses)
  -> if disagreement:
       await queue.put(DisagreementDetected(agents=..., responses=...))
       if flow_mode == LIVE_DEBATE:
           run adjudication streaming (same pattern)
       await queue.put(AdjudicationComplete(winner=..., rationale=...))
  -> calls store.append(session)

tui/app.py  [Textual worker coroutine]
  -> while msg := await queue.get():
       self.post_message(msg)   # routes into Textual message bus

tui/panels.py  [on_token_chunk handler]
  -> self.rich_log.write(msg.text)   # appends to correct agent column

tui/status_bar.py  [on_disagreement_detected, on_adjudication_complete handlers]
  -> updates status label
```

### Key invariant

The queue is the only interface between the async subprocess world and the Textual widget world. All queue messages are immutable dataclasses. No widget ever touches a `subprocess.Process` object directly.

---

## Streaming Implementation Pattern

### Bridge coroutine skeleton

```python
# tui/bridge.py

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass(frozen=True)
class TokenChunk:
    agent_id: str
    text: str

@dataclass(frozen=True)
class AgentDone:
    agent_id: str
    full_text: str

class StreamingOrchestratorBridge:
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue

    async def run_session(self, prompt: str, agent_specs: list[AgentSpec], flow_mode: FlowMode) -> None:
        tasks = [
            asyncio.create_task(self._stream_agent(spec, prompt))
            for spec in agent_specs
        ]
        await asyncio.gather(*tasks)
        # classify, adjudicate, store using existing modules unchanged

    async def _stream_agent(self, spec: AgentSpec, prompt: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            *spec.cmd_args(prompt),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        chunks = []
        while chunk := await proc.stdout.read(256):
            text = chunk.decode("utf-8", errors="replace")
            chunks.append(text)
            await self._queue.put(TokenChunk(agent_id=spec.id, text=text))
        await proc.wait()
        full = "".join(chunks)
        await self._queue.put(AgentDone(agent_id=spec.id, full_text=full))
        return full
```

### TUI worker pattern (Textual)

```python
# tui/app.py

from textual.app import App
from textual.worker import work

class AgentBureauApp(App):
    @work(exclusive=True, thread=False)
    async def run_session(self, prompt: str) -> None:
        queue: asyncio.Queue = asyncio.Queue()
        bridge = StreamingOrchestratorBridge(queue)
        bridge_task = asyncio.create_task(
            bridge.run_session(prompt, self._agent_specs, self._flow_mode)
        )
        while True:
            msg = await queue.get()
            self.post_message(msg)
            if isinstance(msg, SessionComplete):
                break
        await bridge_task
```

Textual's `@work` decorator runs the coroutine inside the Textual event loop, so `post_message` is safe. The queue decouples the bridge's `asyncio.gather` fan-out from the widget's message handlers.

---

## Layout Architecture

### Side-by-side columnar layout

Textual uses CSS-like layout. A `Horizontal` container with N `AgentPanel` children each styled `width: 1fr` produces equal-width columns that fill the terminal width automatically.

```
AgentBureauApp (App)
  Header (agent names, status indicators)
  Horizontal (layout.py -> AgentColumnLayout)
    AgentPanel[claude]    (panels.py)
      Label(agent name + status)
      RichLog (scrollable, streaming tokens land here)
    AgentPanel[gemini]
      Label(agent name + status)
      RichLog
    AgentPanel[gpt-4]
      ...
  StatusBar (status_bar.py)
    Label(flow mode)
    Label(session state)
    Label(disagreement / adjudication result)
  [Modal] FlowPicker (flow_picker.py)  -- shown at session start
```

When a new agent is added (via discovery), a new `AgentPanel` is mounted dynamically: `self.query_one(AgentColumnLayout).mount(AgentPanel(spec))`. No layout code needs to change.

### Responsive column count

Columns use `width: 1fr` in Textual CSS. For large numbers of agents (>4), the app should cap visible columns and allow horizontal scrolling via `overflow-x: auto` on the `Horizontal` container, or paginate with tab navigation.

---

## Per-Session Flow Choice

Flow mode is selected before the session starts via `FlowPicker`, a modal `Screen` subclass.

```python
# tui/flow_picker.py

from textual.screen import ModalScreen
from textual.widgets import Button, Label

class FlowPicker(ModalScreen[FlowMode]):
    def compose(self):
        yield Label("Select session mode:")
        yield Button("Pick one winner", id="pick_one")
        yield Button("Live debate", id="live_debate")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mode = FlowMode.PICK_ONE if event.button.id == "pick_one" else FlowMode.LIVE_DEBATE
        self.dismiss(mode)
```

The app calls `await self.push_screen(FlowPicker())` and receives the selected `FlowMode` back before starting the bridge. This keeps mode selection entirely in the presentation layer; the bridge receives the mode as a parameter.

---

## Agent Discovery

```python
# tui/discovery.py

import shutil
from dataclasses import dataclass

KNOWN_AGENTS = {
    "claude": ["claude", "--output-format", "stream-json", "--print", "{prompt}"],
    "gemini": ["gemini", "--prompt", "{prompt}"],
    "aider": ["aider", "--message", "{prompt}", "--yes"],
}

@dataclass(frozen=True)
class AgentSpec:
    id: str
    display_name: str
    _cmd_template: list[str]

    def cmd_args(self, prompt: str) -> list[str]:
        return [arg.replace("{prompt}", prompt) for arg in self._cmd_template]

def discover_agents() -> list[AgentSpec]:
    found = []
    for name, template in KNOWN_AGENTS.items():
        if shutil.which(template[0]):
            found.append(AgentSpec(id=name, display_name=name.title(), _cmd_template=template))
    return found
```

`discover_agents()` is called once at startup. It merges with any preset overrides. The result is passed to `AgentBureauApp` as `agent_specs`. No runtime PATH scanning happens during a session.

The `KNOWN_AGENTS` registry is the extension point: adding a new CLI agent is a one-line dict entry, with no changes to any other module. This satisfies OCP.

---

## Integration Strategy — Not Breaking Existing Code

### The fundamental rule

The existing `orchestrator.py`, `adapters.py`, `classifier.py`, `adjudication.py`, and `store.py` must not be changed to accommodate the TUI. The bridge wraps them.

### How the bridge wraps the orchestrator

The current `adapters.py` likely uses `subprocess.run` (blocking). The bridge replaces this call path with `asyncio.create_subprocess_exec` for TUI sessions only. Two options:

**Option A (preferred): Bridge bypasses adapters for streaming, calls classifier/adjudication/store directly**

```
Bridge -> asyncio.create_subprocess_exec (own streaming logic)
       -> classifier.classify(collected AgentResponse objects)   [existing, unchanged]
       -> adjudication.run(responses)                            [existing, unchanged]
       -> store.append(session)                                  [existing, unchanged]
```

This means the AgentAdapter protocol is not used in TUI streaming mode. The bridge contains its own subprocess invocation. This is acceptable because the adapter protocol's job (wrapping subprocess invocation) is duplicated but not invalidated — adapters still serve the non-TUI path.

**Option B: Extend AgentAdapter protocol with an async streaming method**

```python
class AgentAdapter(Protocol):
    def invoke(self, prompt: str) -> AgentResponse: ...          # existing
    async def stream(self, prompt: str) -> AsyncIterator[str]: ...  # new
```

Existing adapter implementations provide only `invoke`. The bridge calls `stream` if available, falls back to `invoke` in a thread executor if not. This is cleaner but requires touching `adapters.py`.

**Recommendation: Option A for the first TUI milestone.** It keeps the TUI layer fully isolated and avoids changing tested code. Option B becomes a clean refactor in a later milestone.

### Non-TUI path remains unchanged

```
cli.py --no-tui  (or default)
  -> orchestrator.py -> adapters.py -> classifier -> adjudication -> store
     [all existing code, zero changes]
```

The `--tui` flag in `cli.py` is a branch at the entry point only. Both paths share `models.py`, `classifier.py`, `adjudication.py`, `store.py` without modification.

---

## Suggested Build Order

### Phase 1 — Async subprocess streaming (no TUI)

**Goal:** Prove that the bridge can fan-out to N agents concurrently, stream tokens, collect full responses, and hand off to existing classifier/adjudication/store.

**Components:**
- `tui/event_bus.py` (message dataclasses: TokenChunk, AgentDone, DisagreementDetected, AdjudicationComplete, SessionComplete)
- `tui/bridge.py` (StreamingOrchestratorBridge; asyncio subprocess streaming)
- `tui/discovery.py` (AgentDiscovery; PATH scanning)

**Testable without TUI:** Drive the bridge from a plain `asyncio.run()` test harness. Drain the queue and assert message sequence.

**Why first:** Everything else depends on this. The bridge is the only component that touches both the existing code and the new code. Proving it correct before building the TUI means TUI bugs are isolated to presentation.

### Phase 2 — Static TUI layout (no live streaming)

**Goal:** Render a fixed set of agent columns with placeholder content. Validate that the layout is correct at various terminal widths.

**Components:**
- `tui/panels.py` (AgentPanel widget; static RichLog)
- `tui/layout.py` (AgentColumnLayout; Horizontal container with dynamic mount)
- `tui/status_bar.py` (static labels)
- `tui/app.py` (App stub; mounts layout; no bridge yet)

**Why second:** Layout bugs are easier to diagnose without live data. Terminal width and column overflow behavior must be validated in isolation.

### Phase 3 — Wire bridge to TUI

**Goal:** Live tokens appear in the correct agent column as subprocesses stream.

**Components:**
- `tui/app.py` (connect bridge queue to Textual worker; route messages to panels)
- Update `tui/panels.py` message handlers (on_token_chunk, on_agent_done)
- Update `tui/status_bar.py` message handlers (on_disagreement_detected, on_adjudication_complete)

**Why third:** Both the bridge (Phase 1) and layout (Phase 2) must be verified before connecting them. Connecting is a single-point integration.

### Phase 4 — Flow picker and per-session mode

**Goal:** User selects flow mode before session starts; live debate mode triggers adjudication in real time.

**Components:**
- `tui/flow_picker.py` (FlowPicker modal screen)
- Update `tui/bridge.py` to handle LIVE_DEBATE mode (stream adjudication agent tokens)
- Update `tui/app.py` to push FlowPicker screen before run_session

**Why fourth:** Requires the full streaming pipeline to already work. Flow mode changes only the bridge's adjudication behavior, not the layout.

### Phase 5 — cli.py integration and agent discovery

**Goal:** `disagree --tui` launches the TUI; discovered agents populate the panel layout automatically.

**Components:**
- Update `cli.py` (--tui flag; branch to app.run())
- `tui/discovery.py` wired into `tui/app.py` startup
- System test: real `claude --print` and `aider --message` invocations

**Why last:** Requires all internal components to be stable. Real subprocess invocations introduce external dependencies that are harder to control in tests.

---

## Dependency Diagram (Build Order View)

```
Phase 1:  event_bus.py  <--  bridge.py  <--  discovery.py
                                  |
Phase 2:            panels.py  <-- layout.py  <-- status_bar.py  <-- app.py (stub)
                                                                        |
Phase 3:                                           [connect bridge to app.py]
                                                                        |
Phase 4:                                flow_picker.py  <-- [update bridge + app.py]
                                                                        |
Phase 5:                    [update cli.py + wire discovery into app.py startup]
```

---

## Key Risks and Mitigations

### Risk 1: Textual event loop conflicts with asyncio subprocess tasks

**Problem:** `asyncio.create_subprocess_exec` must run inside the same event loop that Textual uses. If the bridge is run in a thread executor, subprocess tasks won't be awaitable.

**Mitigation:** Use Textual's `@work(thread=False)` decorator (async worker), which runs in the Textual event loop. All bridge coroutines are native async, no threads involved.

### Risk 2: Token chunk boundaries split multi-byte characters

**Problem:** Reading fixed-size chunks (e.g., 256 bytes) from stdout can split UTF-8 sequences at byte boundaries.

**Mitigation:** Use `await proc.stdout.readline()` for line-buffered agents (most CLI agents flush on newlines). For truly streaming agents, maintain a decode buffer with `errors="replace"` and only pass complete decoded characters to the queue.

### Risk 3: Agent CLI processes do not line-buffer when running in a pipe

**Problem:** Many CLI tools switch to full buffering when stdout is not a TTY. Claude CLI with `--output-format stream-json` does stream, but `aider` may not.

**Mitigation:** Use `script -q /dev/null agent_cmd` (macOS/Linux) or a PTY to force TTY mode. The bridge should try PTY first via `asyncio`'s subprocess with a pseudo-terminal, falling back to pipe. Document per-agent buffering behavior in `KNOWN_AGENTS`.

### Risk 4: Adjudication adds latency before TUI shows result

**Problem:** In PICK_ONE mode, the TUI shows all tokens, then goes silent while adjudication runs. Users may think the app has frozen.

**Mitigation:** The status bar transitions to "Adjudicating..." state via `AdjudicationStarted` message as soon as all agents complete. A spinner widget in the status bar confirms activity.

---

## What This Means for the Roadmap (Downstream Implications)

1. **Phase 1 (bridge) is a blocker for everything.** No TUI work can be validated end-to-end without the async streaming bridge. It should be the first phase in the roadmap.

2. **The AgentAdapter protocol decision is a fork.** Option A (bridge bypasses adapters) is faster for the first milestone but creates a maintenance split. Option B (extend protocol) is the right long-term design. The roadmap should plan a refactor phase after TUI stabilizes.

3. **Discovery is low-risk and can be built in parallel with layout.** It has no dependencies on the TUI or the bridge. It can be developed and tested independently in Phase 1.

4. **Testing strategy shifts per phase.** Phase 1 tests are pure asyncio unit tests. Phase 2 tests use Textual's `Pilot` test harness for snapshot/layout testing. Phase 3 tests combine both. This should be reflected in the test plan.

5. **The `--tui` flag in `cli.py` is the integration seam.** Until Phase 5, the TUI path can be developed and tested without touching the existing CLI flow at all. This keeps the existing test suite green throughout.

---

## Sources

This document is based on:
- The milestone context and existing architecture description provided in the task prompt
- The existing source structure discovered at `/Users/jakeogden/agent-bureau/src/disagree_v1/`
- Knowledge of Textual (textualize.io) TUI framework patterns, async worker model, and widget composition API as of August 2025
- Knowledge of `asyncio.create_subprocess_exec`, Python async subprocess patterns, and PTY handling
- General patterns from multi-pane terminal tools (lazygit, k9s, atuin) adapted to Python/Textual context
