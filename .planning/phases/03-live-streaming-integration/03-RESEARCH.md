# Phase 3: Live Streaming Integration - Research

**Researched:** 2026-02-23
**Domain:** Textual asyncio integration, bridge-to-TUI event routing, state machine, disagreement classification
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Prompt input:**
- Input field in the TUI — not a CLI argument
- Fixed one-line bar at the bottom of the screen (below agent panes)
- Layout from top to bottom: status bar / agent panes / prompt input
- Input is blocked/disabled while agents are streaming — no mid-run resubmit
- On new prompt submission: append output below the previous run's content with a visual separator
- Auto-clear panes when content approaches the scrollback limit (5000 lines)
- User can manually clear pane content via a keybinding (e.g., Ctrl-L)

**Status bar:**
- Sits at the very top of the screen, above the agent pane headers
- Shows: per-agent streaming state + token/line counts per agent + disagreement state
- Does NOT show elapsed time
- Initial state (before any prompt): keyboard hints (e.g., "Enter: submit • Ctrl-C: quit • Ctrl-L: clear")
- While streaming: "claude: streaming (42 lines) • codex: streaming (38 lines)"
- After both finish: completion summary (e.g., "Both done — claude: 120 lines, codex: 115 lines")
- After classification: adds disagreement or agreement result to the completion summary

**Disagreement display:**
- Status bar shows disagreement type label
- Both pane headers get a visual highlight when a disagreement is detected (color change or indicator)
- Classification runs once, after both agents finish streaming — no mid-stream classification
- When agents agree: show explicit "agents agree" confirmation in status bar
- When agents disagree: show type label, e.g., "disagreement: approach"

**Streaming behavior:**
- Token-by-token: each token appended to the pane as soon as it arrives
- Agent errors: append a visible error message to the pane content (e.g., "[error: agent exited with code 1]")
- When one agent finishes and the other is still streaming: finished pane just stops — no done marker appended
- User can scroll any pane freely at any time during streaming; new tokens continue appending at the bottom

**Pane content:**
- Pane content persists across runs (append model) — user can review previous runs by scrolling up
- SCROLLBACK_LIMIT (5000) from Phase 2 is the auto-clear threshold — reuse the existing constant
- Both panes clear together when either hits the limit (keep them synchronized)

### Claude's Discretion
- Exact disagreement detail format in the status bar (type label vs type + description — fit to space)
- Run separator visual between successive prompt runs
- Keybinding for manual clear (Ctrl-L suggested but open)
- Auto-scroll behavior when user has scrolled up (standard Textual auto_scroll behavior)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TUI-03 | Agent output streams token-by-token into the correct pane as the agent responds | Asyncio worker + custom Message pattern; `post_message()` is safe from same-loop tasks; route TokenChunk to pane via agent name |
| TUI-09 | Status bar shows current session mode, agent streaming state, and adjudication status | `Static` widget updated via `Static.update()`; reactive `session_state` drives status text |
| ORCH-02 | Both agents run in parallel from the moment the prompt is submitted | Bridge already does this; `_stream_pty` / `_stream_pipe` run as concurrent `asyncio.create_task()` inside an asyncio worker |
| ORCH-03 | Disagreements between agents are visualized in the TUI | `classify_disagreements()` called after both `AgentDone` received; results drive pane header class toggle + status bar update |
| ORCH-06 | State machine gates all transitions — streaming completes before any apply step begins | `SessionState` enum (`IDLE / STREAMING / CLASSIFYING / DONE`) stored as reactive; `Input.disabled` toggled by state; classification blocked until both terminal events received |
</phase_requirements>

---

## Summary

Phase 3 wires the existing async bridge (Phase 1) to the existing TUI (Phase 2). The central challenge is connecting two asyncio-native systems: the bridge posts events to an `asyncio.Queue`, and Textual's message pump also runs on the same asyncio event loop. Because both live on the same event loop thread, calling `app.post_message()` from a coroutine scheduled with `asyncio.create_task()` is safe — Textual's `post_message()` implementation detects same-thread callers and uses `put_nowait()` directly (no `call_from_thread()` needed).

The recommended architecture uses Textual's `run_worker()` on an async method that directly owns the bridge queue and dispatches custom Message subclasses to the app for each event. This keeps the bridge code untouched and avoids threading complexity. A `SessionState` enum (IDLE / STREAMING / CLASSIFYING / DONE) stored as a reactive attribute on the app drives all state-dependent UI: Input disabled state, status bar text, and pane header highlights.

The `disagree_v1.classifier.classify_disagreements()` function expects structured `AgentResponse` objects, which the current bridge does not produce. For Phase 3, the recommended approach is to configure `AgentSpec` with JSON-output flags (matching the `presets.py` pattern) so `AgentDone.full_text` can be parsed by the existing `CommandJsonAdapter._parse_payload()` logic. If parsing fails, show a graceful fallback ("classification unavailable"). This avoids building a new classifier while reusing proven code.

**Primary recommendation:** Use Textual's `run_worker()` with a single async worker method that owns the bridge queue, routes events via custom `Message` subclasses to the app, and triggers classification after both terminal events arrive.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | >=0.80.0,<9 (installed: 8.0.0) | TUI framework, event loop, widgets | Already in use; asyncio-native; provides `Input`, `Static`, `run_worker()` |
| rich | (bundled with textual) | `AnsiDecoder`, `Text`, `Syntax` renderable types | Already in use via `write_content_to_pane`; handles ANSI from agent output |
| asyncio | stdlib | Event loop, Queue, create_task | Bridge is already asyncio-native; same loop as Textual |
| disagree_v1.classifier | project | `classify_disagreements(AgentResponse, AgentResponse) -> list[Disagreement]` | Existing, synchronous, tested |
| disagree_v1.adapters | project | `CommandJsonAdapter._parse_payload()` for JSON extraction from `full_text` | Existing JSON parser; reuse to avoid duplication |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| enum.Enum | stdlib | `SessionState` state machine enum | Model IDLE/STREAMING/CLASSIFYING/DONE as explicit states |
| rich.ansi.AnsiDecoder | (rich) | Decode ANSI escape sequences from agent output into `rich.text.Text` | In streaming write path; agent CLIs emit ANSI color codes |
| dataclasses | stdlib | Custom `Message` subclasses | Define `TokenReceived`, `AgentFinished`, `ClassificationDone` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `run_worker()` async method | `asyncio.create_task()` directly in `on_mount` | `run_worker()` integrates with Textual's worker lifecycle (cancel on exit, error surfacing); direct tasks are harder to cancel cleanly |
| `post_message()` from coroutine | `call_from_thread()` | `call_from_thread()` is for actual threads; same-loop coroutines use `post_message()` directly — no overhead |
| `Static` for status bar | Custom `Widget` subclass | `Static.update()` is sufficient for text; a full custom widget adds complexity with no benefit for Phase 3 |
| `CommandJsonAdapter._parse_payload()` reuse | New ad-hoc JSON parser | Reuse tested code; avoid duplication |

**Installation:** No new dependencies. All required libraries are already installed.

---

## Architecture Patterns

### Recommended Project Structure (Phase 3 additions)

```
src/tui/
├── app.py              # AgentBureauApp — extended with session state, workers, message handlers
├── bridge.py           # Unchanged — _stream_pty/_stream_pipe/_pty_available imported directly
├── content.py          # Unchanged — SCROLLBACK_LIMIT constant reused
├── event_bus.py        # Unchanged — TokenChunk, AgentDone, AgentError, AgentTimeout
├── messages.py         # NEW — TokenReceived, AgentFinished, ClassificationDone (Textual Message subclasses)
├── session.py          # NEW — SessionState enum, session orchestration logic
├── widgets/
│   ├── agent_pane.py   # Extended — add clear(), set_disagreement_highlight()
│   ├── prompt_bar.py   # NEW — Input widget wrapper (one-line bar at bottom)
│   ├── status_bar.py   # NEW — Static widget wrapper (one-line bar at top)
│   └── quit_screen.py  # Unchanged
└── styles.tcss         # Extended — status bar, prompt bar, disagreement highlight styles
```

### Pattern 1: Textual Message Bus for Bridge Events

**What:** Define custom `Message` subclasses that wrap bridge events. The async worker calls `self.post_message()` for each queue event. Handlers on the app route to panes and status bar.

**When to use:** Always — this is the only safe way to update Textual widgets from an async task running on the same event loop.

**Why it is safe:** `MessagePump.post_message()` checks `threading.get_ident()` vs `self._thread_id`. An `asyncio.create_task()` runs on the same thread as Textual's event loop, so the check passes and `_message_queue.put_nowait(message)` is called directly. No `call_from_thread()` needed.

```python
# Source: verified from textual/message_pump.py source (Textual 8.0.0)

# src/tui/messages.py
from __future__ import annotations
from dataclasses import dataclass
from textual.message import Message
from tui.event_bus import BridgeEvent

@dataclass
class TokenReceived(Message):
    agent: str
    text: str

@dataclass
class AgentFinished(Message):
    agent: str
    event: BridgeEvent  # AgentDone | AgentError | AgentTimeout

@dataclass
class ClassificationDone(Message):
    disagreements: list  # list[disagree_v1.models.Disagreement]
```

### Pattern 2: Asyncio Worker Owning the Bridge Queue

**What:** An async method decorated with `@work` (or called via `self.run_worker()`) directly controls the bridge's `asyncio.Queue`. It spawns the agent tasks and reads events as they arrive, posting Textual messages for each.

**When to use:** On each prompt submission. Cancel any previous worker first.

```python
# Source: verified from textual.work decorator and bridge.py source

# In AgentBureauApp:
async def _run_session(self, prompt: str) -> None:
    """Async worker: owns the bridge queue, dispatches Textual messages."""
    from tui.bridge import _stream_pty, _stream_pipe, _pty_available
    from tui.event_bus import AgentSpec
    import asyncio

    _stream = _stream_pty if _pty_available() else _stream_pipe
    q: asyncio.Queue = asyncio.Queue()

    task_a = asyncio.create_task(_stream(CLAUDE, prompt, timeout=60.0, q=q))
    task_b = asyncio.create_task(_stream(CODEX, prompt, timeout=60.0, q=q))

    done_count = 0
    while done_count < 2:
        event = await q.get()
        if event.type == "token":
            self.post_message(TokenReceived(agent=event.agent, text=event.text))
        else:
            done_count += 1
            self.post_message(AgentFinished(agent=event.agent, event=event))

    await asyncio.gather(task_a, task_b)
    # Classification happens in on_agent_finished after both terminal events received
```

**Key detail:** `_stream_pty` and `_stream_pipe` accept `q` as a parameter — the worker creates and owns the queue. The bridge's `run_bridge()` function is NOT used here (it collects all events before returning); instead, the private streaming functions are called directly.

### Pattern 3: SessionState Reactive for State Machine (ORCH-06)

**What:** A `reactive` attribute on the app stores the current session state as an enum. A `watch_` method updates all state-dependent UI atomically.

**When to use:** Every state transition (IDLE -> STREAMING -> CLASSIFYING -> DONE -> IDLE).

```python
# Source: verified from textual.reactive source (Textual 8.0.0)

from enum import Enum, auto
from textual.reactive import reactive

class SessionState(Enum):
    IDLE = auto()
    STREAMING = auto()
    CLASSIFYING = auto()
    DONE = auto()

class AgentBureauApp(App):
    session_state: reactive[SessionState] = reactive(SessionState.IDLE)

    def watch_session_state(self, state: SessionState) -> None:
        """Called automatically when session_state changes."""
        prompt_bar = self.query_one("#prompt-bar", Input)
        prompt_bar.disabled = state in (SessionState.STREAMING, SessionState.CLASSIFYING)
        # Status bar update handled by separate method
```

### Pattern 4: Static Status Bar with Direct Update

**What:** A `Static` widget at the top of the layout. Its text is updated by calling `static_widget.update(new_text)` in message handlers. No reactive binding needed.

**When to use:** Any time agent state changes — each token count update, each agent finish, after classification.

```python
# Source: verified from textual.widgets.Static.update signature (Textual 8.0.0)

# In message handler:
def on_token_received(self, message: TokenReceived) -> None:
    pane = self._get_pane(message.agent)
    pane.write_token(message.text)
    self._update_status_bar()

def _update_status_bar(self) -> None:
    status = self.query_one("#status-bar", Static)
    status.update(self._build_status_text())
```

### Pattern 5: Input Widget for Prompt Bar

**What:** A `textual.widgets.Input` widget at the bottom. Handles `Input.Submitted` message (fires on Enter). Cleared after submission via `input.clear()`. Disabled during streaming via `input.disabled = True`.

**Key API (verified Textual 8.0.0):**
- `Input(placeholder="...", id="...", compact=True)` — compact removes outer border
- `input.disabled = True / False` — blocks interaction while streaming
- `input.clear()` — clears value after submission
- `input.focus()` — returns focus to input after session completes
- Message handler: `def on_input_submitted(self, event: Input.Submitted) -> None:` — `event.value` contains the prompt text

```python
# Source: verified from textual.widgets._input source (Textual 8.0.0)

def on_input_submitted(self, event: Input.Submitted) -> None:
    prompt = event.value.strip()
    if not prompt or self.session_state != SessionState.IDLE:
        return
    event.input.clear()
    self.session_state = SessionState.STREAMING
    self.run_worker(self._run_session(prompt), exclusive=True, exit_on_error=False)
```

### Pattern 6: ANSI Token Display in RichLog

**What:** Agent CLI output contains ANSI escape codes. The bridge passes them through raw. Use `rich.ansi.AnsiDecoder` to convert each token line to a `rich.text.Text` object before writing to `RichLog`.

**When to use:** In `AgentPane.write_token()` for live streaming (distinct from `write_content()` which handles multi-line blocks with fenced code).

```python
# Source: verified from rich.ansi.AnsiDecoder, rich.text.Text (Rich bundled with Textual 8.0.0)

from rich.ansi import AnsiDecoder
from rich.text import Text

_decoder = AnsiDecoder()

def write_token(self, line: str) -> None:
    """Write a single streamed token line to the RichLog."""
    log = self.query_one("#content", RichLog)
    if not self._has_content:
        self._has_content = True
        self.query_one("#placeholder", Label).display = False
        log.display = True
    # Convert ANSI to Rich Text safely
    rich_text = next(_decoder.decode(line), Text(line))
    log.write(rich_text)
```

### Pattern 7: Line Counting for Status Bar

**What:** Track per-agent line counts for status bar display. `RichLog.lines` is a public `list[Strip]` attribute — `len(log.lines)` gives the current line count.

**Note:** This is an internal API (no stable line_count property exists in Textual 8.0.0). A safer alternative is maintaining a counter in `AgentPane` incremented on each `write_token()` call.

**Recommended:** Maintain `self._line_count: int = 0` in `AgentPane`, increment in `write_token()`, and expose as a property. Avoids internal API reliance.

### Anti-Patterns to Avoid

- **Calling `write_content()` per token:** `write_content_to_pane()` uses `splitlines()` and fenced code parsing — designed for complete multi-line blocks, not per-line tokens. Use a separate `write_token()` method for streaming.
- **Using `call_from_thread()` from coroutines:** Only needed for actual threads (`thread=True` workers). Same-loop coroutines use `post_message()` directly.
- **Modifying widgets from inside `_run_session` directly:** Never call `pane.write_token()` from inside the worker coroutine — always route through `post_message()`.
- **Using `run_bridge()` for streaming:** `run_bridge()` collects all events and returns them as a list after completion — not suitable for real-time streaming. Use the private `_stream_pty`/`_stream_pipe` functions directly.
- **Classifying before both terminal events:** `classify_disagreements()` must only be called after both `AgentFinished` messages with non-token types are received. Gate with a counter or set.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe UI updates from async tasks | Custom synchronization primitives | `post_message()` from same-loop coroutines | Textual's message pump is the correct channel; already handles thread detection |
| JSON extraction from agent output | New parser | `CommandJsonAdapter._parse_payload()` from `disagree_v1.adapters` | Already tested, handles both pure JSON and JSON-embedded-in-text |
| Disagreement classification | New text similarity / NLP code | `classify_disagreements()` from `disagree_v1.classifier` | Existing, tested, produces correct `Disagreement.kind` labels (approach/fact/confidence_gap) |
| ANSI-safe text rendering | Strip ANSI codes | `rich.ansi.AnsiDecoder` | Rich already bundled; handles ANSI → `Text` conversion; preserves agent colors |
| Worker lifecycle management | Manual task tracking | `self.run_worker(..., exclusive=True)` | Textual cancels previous exclusive worker automatically before starting new one |

**Key insight:** All infrastructure for this phase already exists across `disagree_v1`, `rich`, and `textual`. Phase 3 is wiring, not building.

---

## Common Pitfalls

### Pitfall 1: Using `run_bridge()` for Streaming
**What goes wrong:** `run_bridge()` blocks until both agents complete, then returns all events as a list. Calling it in a worker means no tokens appear until both agents are done — completely defeats real-time streaming.
**Why it happens:** The function signature looks like the right entry point.
**How to avoid:** Import and call `_stream_pty` / `_stream_pipe` directly with a shared `asyncio.Queue`. Create tasks for both agents concurrently and read from the queue as events arrive.
**Warning signs:** Panes only update after a long pause, then all content appears at once.

### Pitfall 2: Classifying Before Both Agents Finish
**What goes wrong:** `classify_disagreements()` called with only one `AgentDone` — second agent's text is missing. Results are meaningless or crash.
**Why it happens:** `on_agent_finished` fires for each agent individually.
**How to avoid:** Track terminal events in a dict keyed by agent name. Only call classification when both terminal events are present. ORCH-06 requirement: state machine enforces this.
**Warning signs:** `KeyError` on second agent lookup, or classification showing only one agent's data.

### Pitfall 3: Marking Textual Widgets from Wrong Thread
**What goes wrong:** Calling widget methods from a `thread=True` worker (actual thread) without `call_from_thread()` — causes race conditions, corrupted state, silent failures.
**Why it happens:** Confusing thread workers with async workers.
**How to avoid:** Use async workers (default `thread=False`) for bridge integration. If a thread worker is ever needed, always use `call_from_thread()` or `post_message()`.
**Warning signs:** Intermittent rendering corruption, messages processed out of order.

### Pitfall 4: ANSI Sequences Interpreted as Rich Markup
**What goes wrong:** If `log.write(raw_ansi_string)` is called on a `RichLog` with `markup=True`, Rich may try to interpret ANSI `\x1b[` sequences as markup — leading to parse errors or garbled output.
**Why it happens:** The existing `RichLog` is configured with `markup=True` for fenced code rendering.
**How to avoid:** Always pass ANSI lines through `AnsiDecoder` first. The resulting `rich.text.Text` object is markup-safe.
**Warning signs:** `[bold` or `[/` appearing literally in pane content; `MarkupError` exceptions.

### Pitfall 5: `tests/tui/__init__.py` Breaking sys.path
**What goes wrong:** If `tests/tui/__init__.py` exists, pytest's sys.path resolution makes `tests/tui/` shadow `src/tui/`, causing import errors.
**Why it happens:** Documented in STATE.md from Phase 01-02 discovery.
**How to avoid:** Keep `tests/tui/__init__.py` absent. This is the established project rule.
**Warning signs:** `ImportError: cannot import name 'AgentPane' from 'tui.widgets'` in tests.

### Pitfall 6: Integration Tests Running Inside Claude Code
**What goes wrong:** The `claude` CLI refuses to run when the `CLAUDECODE` environment variable is set (nested session detection). Real-subprocess integration tests fail.
**Why it happens:** Documented in STATE.md from Phase 01-03 discovery.
**How to avoid:** Phase 3 integration tests that invoke real agents must run outside Claude Code with `CLAUDECODE` unset. Use `FakeAgentRunner` pattern from `tests/tui/test_bridge.py` for all in-session tests.
**Warning signs:** `claude` subprocess exits immediately with an error message about nested sessions.

### Pitfall 7: Scrollback Synchronization
**What goes wrong:** One pane auto-clears at 5000 lines but the other does not — panes become desynchronized (one shows old content, the other shows new).
**Why it happens:** Each pane manages its own `RichLog.max_lines` independently.
**How to avoid:** When checking line count in `write_token()`, if either pane exceeds `SCROLLBACK_LIMIT`, clear both panes simultaneously via the app (not from within the pane itself). The app owns the synchronization decision.
**Warning signs:** One pane jumps to a new run's content while the other still shows the previous run.

---

## Code Examples

Verified patterns from official sources and direct inspection of Textual 8.0.0 installed in `.venv`:

### Custom Textual Message Definition

```python
# Source: verified textual.message.Message API (Textual 8.0.0)
# Handler name for top-level class TokenReceived -> on_token_received
# Handler name for top-level class AgentFinished -> on_agent_finished
# Handler name for top-level class ClassificationDone -> on_classification_done

from __future__ import annotations
from dataclasses import dataclass
from textual.message import Message
from tui.event_bus import BridgeEvent


@dataclass
class TokenReceived(Message):
    """A single streamed token line from an agent."""
    agent: str
    text: str


@dataclass
class AgentFinished(Message):
    """An agent's terminal event (done/error/timeout)."""
    agent: str
    event: BridgeEvent


@dataclass
class ClassificationDone(Message):
    """Disagreement classification results ready."""
    disagreements: list  # list[Disagreement]
    full_texts: dict     # {agent_name: str} for status bar
```

### Input Widget Layout (Bottom Prompt Bar)

```python
# Source: verified textual.widgets.Input.__init__ (Textual 8.0.0)
# compact=True removes the default Input border (matches flat bar aesthetic)
# disabled=False on init; toggled during streaming

from textual.widgets import Input

# In AgentBureauApp.compose():
yield Input(
    placeholder="Enter a prompt and press Enter...",
    id="prompt-bar",
    compact=True,
)
```

### Input Submission Handler

```python
# Source: verified Input.Submitted dataclass (Textual 8.0.0)
# event.value is the submitted string
# event.input.clear() clears the field

def on_input_submitted(self, event: Input.Submitted) -> None:
    prompt = event.value.strip()
    if not prompt or self.session_state != SessionState.IDLE:
        return
    event.input.clear()
    self._start_session(prompt)

def _start_session(self, prompt: str) -> None:
    self.session_state = SessionState.STREAMING
    self._terminal_events: dict[str, BridgeEvent] = {}
    self._write_run_separator()
    self.run_worker(
        self._run_session(prompt),
        exclusive=True,
        exit_on_error=False,
        name="bridge-session",
    )
```

### Async Worker Pattern (Bridge to TUI)

```python
# Source: verified tui.bridge._stream_pty/_stream_pipe signatures + asyncio.Queue (Textual 8.0.0)

async def _run_session(self, prompt: str) -> None:
    """Worker: fan-out to bridge, dispatch Textual messages per event."""
    from tui.bridge import _stream_pty, _stream_pipe, _pty_available
    from tui.bridge import CLAUDE, CODEX
    import asyncio

    _stream = _stream_pty if _pty_available() else _stream_pipe
    q: asyncio.Queue = asyncio.Queue()

    task_a = asyncio.create_task(
        _stream(CLAUDE, prompt, timeout=60.0, q=q)
    )
    task_b = asyncio.create_task(
        _stream(CODEX, prompt, timeout=60.0, q=q)
    )

    done_count = 0
    while done_count < 2:
        event = await q.get()
        if event.type == "token":
            self.post_message(TokenReceived(agent=event.agent, text=event.text))
        else:
            done_count += 1
            self.post_message(AgentFinished(agent=event.agent, event=event))

    await asyncio.gather(task_a, task_b)
```

### Token Routing and Pane Write

```python
# Source: verified AgentPane.write_content() interface (src/tui/widgets/agent_pane.py)
# New write_token() method needed for per-line streaming

def on_token_received(self, message: TokenReceived) -> None:
    pane_id = "#pane-left" if message.agent == "claude" else "#pane-right"
    pane = self.query_one(pane_id, AgentPane)
    pane.write_token(message.text)
    self._update_status_bar()
```

### Classification After Both Done

```python
# Source: verified disagree_v1.classifier.classify_disagreements signature
# Synchronous — safe to call from a Textual message handler (main event loop)

def on_agent_finished(self, message: AgentFinished) -> None:
    self._terminal_events[message.agent] = message.event
    self._update_status_bar()

    if len(self._terminal_events) == 2:
        self.session_state = SessionState.CLASSIFYING
        self._run_classification()

def _run_classification(self) -> None:
    from disagree_v1.classifier import classify_disagreements
    from disagree_v1.models import AgentResponse
    from disagree_v1.adapters import CommandJsonAdapter

    adapter = CommandJsonAdapter(name="parser", command_template="")
    texts = {
        agent: ev.full_text
        for agent, ev in self._terminal_events.items()
        if ev.type == "done"
    }

    try:
        responses = {
            agent: AgentResponse(**adapter._validate_payload(
                adapter._parse_payload(text)
            ).__dict__)
            for agent, text in texts.items()
        }
        if len(responses) == 2:
            agents = list(responses.values())
            disagreements = classify_disagreements(agents[0], agents[1])
        else:
            disagreements = []
    except (ValueError, Exception):
        disagreements = []  # Classification unavailable; show graceful fallback

    self.post_message(ClassificationDone(
        disagreements=disagreements,
        full_texts=texts,
    ))
```

### Disagreement Header Highlight

```python
# Source: verified Textual add_class/remove_class API (Textual 8.0.0)
# Add CSS class to pane header when disagreement detected

def on_classification_done(self, message: ClassificationDone) -> None:
    self.session_state = SessionState.DONE
    self.query_one("#prompt-bar", Input).focus()

    if message.disagreements:
        self.query_one("#pane-left", AgentPane).add_class("disagreement")
        self.query_one("#pane-right", AgentPane).add_class("disagreement")
    else:
        self.query_one("#pane-left", AgentPane).remove_class("disagreement")
        self.query_one("#pane-right", AgentPane).remove_class("disagreement")

    self._update_status_bar_with_classification(message.disagreements)
```

```css
/* styles.tcss addition */
AgentPane.disagreement #header {
    background: $warning-darken-1;
    color: $text;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `call_from_thread()` for all cross-context calls | `post_message()` for same-loop coroutines; `call_from_thread()` only for actual threads | Textual docs clarification | Simpler async workers; no thread overhead |
| Blocking bridge (`run_bridge()` collects all) | Streaming bridge (`_stream_pty`/`_stream_pipe` with queue consumer) | Phase 3 requirement | Real-time token display |
| Static placeholder content | Input + worker + message routing | Phase 3 | Live interactive app |

**Deprecated/outdated:**
- `run_bridge()` for interactive use: returns only after completion; not suitable for streaming display. Still correct for batch/test use.

---

## Open Questions

1. **Classification with non-JSON agent output**
   - What we know: `classify_disagreements()` needs structured `AgentResponse`; the bridge streams raw text; `CommandJsonAdapter._parse_payload()` can extract JSON from text
   - What's unclear: Whether `claude` and `codex` CLIs (without JSON flags in `AgentSpec.args`) ever produce parseable JSON in their raw output
   - Recommendation: In Phase 3 plan, configure `CLAUDE` and `CODEX` `AgentSpec` with JSON-output flags (e.g., `claude --output-format json`) so `full_text` is JSON-parseable. If classification fails, show "classification unavailable" in status bar — never crash.

2. **Auto-scroll vs user scroll interaction**
   - What we know: `RichLog` has `auto_scroll=True` by default; user can scroll up during streaming
   - What's unclear: Whether Textual 8.0.0's `auto_scroll` continues appending at the bottom correctly when the user has scrolled up
   - Recommendation: CONTEXT.md defers this to "standard Textual auto_scroll behavior" — accept default behavior and test manually. Do not implement custom scroll logic.

3. **`_parse_payload()` method visibility**
   - What we know: `CommandJsonAdapter._parse_payload()` is a private method (single underscore)
   - What's unclear: Stability of accessing it directly
   - Recommendation: Either accept the private access (pragmatic for Phase 3), or extract the parsing logic into a new public function in a `tui/parsing.py` module. Prefer the latter for clean architecture per SRP.

---

## Sources

### Primary (HIGH confidence)
- Textual 8.0.0 installed at `/Users/jakeogden/agent-bureau/.venv` — all API signatures verified via `inspect` and `help()` directly against installed code
- `src/tui/bridge.py` — read directly; confirmed `_stream_pty`, `_stream_pipe`, `_pty_available` are importable; confirmed `asyncio.Queue` parameter interface
- `src/tui/widgets/agent_pane.py` — read directly; confirmed `write_content()` interface and `RichLog` configuration
- `src/tui/event_bus.py` — read directly; confirmed `TokenChunk`, `AgentDone`, `AgentError`, `AgentTimeout` types and `.type` literals
- `src/disagree_v1/classifier.py` — read directly; confirmed synchronous, takes `AgentResponse`, returns `list[Disagreement]`
- `src/disagree_v1/models.py` — read directly; confirmed `AgentResponse` fields and `Disagreement.kind` values
- `src/disagree_v1/adapters.py` — read directly; confirmed `CommandJsonAdapter._parse_payload()` and `_validate_payload()` JSON extraction logic
- `textual.message_pump.MessagePump.post_message` — source inspected directly; confirmed thread-detection logic (`threading.get_ident()`) and same-thread `put_nowait()` path

### Secondary (MEDIUM confidence)
- `rich.ansi.AnsiDecoder` — tested directly against installed rich; confirmed `decode()` returns generator of `Text` objects
- `RichLog.lines` — source inspected; confirmed public `list[Strip]` attribute; no `line_count` property exists in 8.0.0

### Tertiary (LOW confidence)
- Classification JSON flag approach (configuring `AgentSpec` with `--output-format json`): based on `presets.py` pattern; actual CLI flag compatibility with current `claude`/`codex` versions not verified (blocked by nested session detection)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified from installed code
- Architecture: HIGH — all patterns verified from source inspection of installed Textual 8.0.0
- Bridge-to-TUI integration: HIGH — `post_message()` thread-safety logic read from source
- Classification integration: MEDIUM — `classify_disagreements()` verified; JSON flag approach is LOW (CLI not testable in this session)
- Pitfalls: HIGH — most derived from existing STATE.md decisions and direct code inspection

**Research date:** 2026-02-23
**Valid until:** 2026-03-25 (Textual 8.x is stable; disagree_v1 is frozen)
