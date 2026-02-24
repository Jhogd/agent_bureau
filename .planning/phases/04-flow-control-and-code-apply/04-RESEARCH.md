# Phase 4: Flow Control and Code Apply - Research

**Researched:** 2026-02-24
**Domain:** Textual 8 modal screens, OptionList navigation, asyncio event signaling, difflib unified diff, atomic file write
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Flow-picker modal**
- Appears as a slim top-banner prompt, not a full-screen overlay or centered dialog
- Navigation: arrow keys to move between options, Enter to confirm
- Default selection: pick-one is pre-highlighted (fastest common path)
- Ctrl-C quits the app from the flow-picker (standard exit, no forced flow choice)

**Live-debate round control**
- Round boundaries are marked by a horizontal divider line inserted into each agent pane (e.g. `── Round 2 ──`)
- User ends the debate early with Esc
- Pressing Esc shows a confirm prompt before stopping ("End debate? [y/n]"), then moves to pick-winner
- Max rounds: Claude's discretion (pick a sensible default during planning)

**Pick-winner UX**
- Pick-winner appears after both agents finish streaming (not mid-stream)
- Four-option menu (top-banner or overlay):
  1. Agent A wins
  2. Agent B wins
  3. Keep discussing (returns to debate)
  4. Cancel (clears context, no files written)
- No extra pane highlight — the four-option menu is sufficient

**Agent reconciliation and code apply**
- When an agent wins (or debate ends), both agents are fed each other's proposals and produce a plain-language discussion of differences and how to reconcile
- Agents converge on agreed code changes through this discussion
- User sees: the agents' plain-language reconciliation discussion + the final agreed code block in the preview pane (overlay/panel below existing panes)
- Diff format: unified diff (standard -/+ lines) for any code shown
- Confirmation gate: user presses y to write, n to reject — single y/n covers all files at once
- No file is ever written without the explicit y confirmation

### Claude's Discretion
- Max rounds default in live-debate mode
- Exact reconciliation prompt design (how agents are instructed to compare and converge)
- How partial/failed reconciliation is handled (agents can't agree)
- Temp file handling during apply

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ORCH-01 | User is prompted at the start of each session to choose a flow: pick-one or live-debate | `FlowPickerScreen(ModalScreen[str])` pushed from worker via `push_screen(wait_for_dismiss=True)`; `OptionList` with `Option("Pick one", id="pick-one")` + `Option("Live debate", id="live-debate")`; dismiss returns `option_id` string |
| ORCH-04 | In live-debate mode, user watches each round of agent exchange stream in real time | Debate loop inside worker: each round calls `_stream_pty/pipe` for both agents sequentially (A sees B's last, B sees A's last); `TokenReceived` messages route tokens to panes as in Phase 3; `RoundBoundary` message appends divider line to both panes |
| ORCH-05 | In live-debate mode, user controls when to end the debate (keypress) | `asyncio.Event` (`self._debate_stop`) set by Esc key handler via `ConfirmEndDebateScreen`; debate loop checks `_debate_stop.is_set()` between rounds; on exit transitions to pick-winner |
| APPLY-01 | When an agent proposes file changes, user sees a diff preview before anything is written | `ReconciliationPanel` widget (RichLog) shows reconciliation text + `Syntax(diff_text, "diff", theme="monokai")`; `difflib.unified_diff()` computes diff between winner's code and current file content |
| APPLY-02 | User must explicitly confirm (keypress) before any file is written to disk | `ApplyConfirmScreen(ModalScreen[bool])` with `BINDINGS = [Binding("y", "confirm"), Binding("n", "reject")]`; `dismiss(True/False)`; file write only if result is `True` |
| APPLY-03 | User can pick which agent's proposed changes to apply (pick-winner flow) | `WinnerPickerScreen(ModalScreen[str])` with `OptionList` of 4 options (agent-a, agent-b, keep-discussing, cancel); `option_id` drives code apply |
</phase_requirements>

---

## Summary

Phase 4 extends the existing Textual 8 TUI with modal screens for flow control, a round-based debate loop, and a gated file-write pipeline. The entire implementation builds on existing patterns: `ModalScreen[T]` for all modal prompts (consistent with `QuitScreen`), `run_worker()` with `push_screen(wait_for_dismiss=True)` for async modal-then-continue flows, and `post_message()` for routing events from workers to the app.

The flow-picker, pick-winner, and apply-confirm screens are all `ModalScreen` subclasses that `dismiss()` with typed values. The worker coroutine `_run_session` drives all state transitions by awaiting screen dismissals and checking `SessionState`. Live-debate rounds are managed by a `while` loop inside the worker, gated by an `asyncio.Event` (`_debate_stop`) that the Esc key handler can set after user confirmation. This avoids any threading complexity.

Code apply uses Python's stdlib `difflib.unified_diff()` for generating the unified diff shown in the `ReconciliationPanel`. File writes use an atomic pattern (write to temp file, rename to target) to prevent partial writes. The single `y/n` confirmation gate covers all files in a session. Because the existing `content.py` already has `Syntax(code, language, theme="monokai")` rendering, diff display reuses the same `RichLog.write(Syntax(...))` pattern with `language="diff"`.

**Primary recommendation:** Implement all modal screens as `ModalScreen[T]` subclasses using `OptionList` for navigation, and drive all state transitions from the `_run_session` worker using `push_screen(wait_for_dismiss=True)`. Never write files without an `ApplyConfirmScreen` gate.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.0.0 (installed) | TUI framework, ModalScreen, OptionList, workers | Already in use; all Phase 3 patterns apply |
| difflib | stdlib | `unified_diff()` for code comparison | No extra install; standard, deterministic |
| pathlib | stdlib | Atomic file writes via `Path.write_text()` | Already used in project; clean Path API |
| tempfile | stdlib | Temp file for atomic write pattern | No extra install; prevents partial writes |
| asyncio | stdlib | `asyncio.Event` for debate stop signal | Already used in bridge and worker patterns |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich.syntax | bundled with textual | `Syntax(diff_text, "diff", theme="monokai")` | Diff display in ReconciliationPanel |
| re | stdlib | Code block extraction (FENCE_OPEN/FENCE_CLOSE reuse) | Parsing agent output for file proposals |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `difflib.unified_diff` | `diff` subprocess | stdlib is simpler, no subprocess overhead, deterministic |
| `OptionList` for picker menus | `SelectionList`, `Button` grid | OptionList has built-in up/down/enter nav matching CONTEXT.md spec exactly |
| `asyncio.Event` for debate stop | Worker `cancel()` | Event is cleaner: lets current round finish gracefully; cancel is abrupt |
| Atomic rename for file write | Direct `Path.write_text()` | Atomic rename prevents data loss on crash mid-write |

**Installation:** No new packages required. All stdlib and textual (already installed).

---

## Architecture Patterns

### Recommended Project Structure

```
src/tui/
├── app.py                      # AgentBureauApp — extended with Phase 4 state + handlers
├── session.py                  # SessionState extended: FLOW_PICK, DEBATING, PICK_WINNER,
│                               #   RECONCILING, CONFIRMING_APPLY
├── messages.py                 # New messages: RoundBoundary, ReconciliationReady, ApplyResult
├── apply.py                    # NEW — extract_code_proposals(), write_files() atomic writer
├── widgets/
│   ├── flow_picker_screen.py   # NEW — FlowPickerScreen(ModalScreen[str])
│   ├── winner_picker_screen.py # NEW — WinnerPickerScreen(ModalScreen[str])
│   ├── end_debate_screen.py    # NEW — ConfirmEndDebateScreen(ModalScreen[bool])
│   ├── apply_confirm_screen.py # NEW — ApplyConfirmScreen(ModalScreen[bool])
│   ├── reconciliation_panel.py # NEW — ReconciliationPanel widget (RichLog wrapper)
│   ├── agent_pane.py           # UNCHANGED
│   ├── status_bar.py           # EXTENDED — show_debating(), show_pick_winner(), etc.
│   ├── quit_screen.py          # UNCHANGED
│   └── prompt_bar.py           # UNCHANGED
└── styles.tcss                 # EXTENDED — Phase 4 CSS appended (OCP compliance)
```

### Pattern 1: Modal Screen Pushed from Worker with wait_for_dismiss

**What:** A worker coroutine calls `self.push_screen(screen, wait_for_dismiss=True)` to pause the worker until the user makes a choice, then continues with the result.

**When to use:** Any time a modal prompt must gate async work (flow pick, winner pick, apply confirm).

```python
# Source: Textual 8 push_screen API (verified via inspection 2026-02-24)
# Inside _run_session (a worker coroutine):
async def _run_session(self, prompt: str) -> None:
    # Step 1: Ask user to choose flow
    flow: str = await self.push_screen(
        FlowPickerScreen(),
        wait_for_dismiss=True,  # MUST be True when awaiting from worker
    )
    # flow == "pick-one" or "live-debate"
    if flow == "live-debate":
        await self._run_live_debate(prompt)
    else:
        await self._run_pick_one(prompt)
```

**Key constraint:** `wait_for_dismiss=True` only works from inside a worker. Calling it outside a worker raises `NoActiveWorker`.

### Pattern 2: OptionList-Based Modal Screen

**What:** `ModalScreen[str]` using `OptionList` for keyboard navigation. User uses up/down to highlight, Enter to select. Screen dismisses with the selected option's `id`.

**When to use:** Flow picker and winner picker screens.

```python
# Source: Textual 8 OptionList API (verified via inspection 2026-02-24)
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets._option_list import Option


class FlowPickerScreen(ModalScreen[str]):
    """Slim top-banner flow picker. Returns 'pick-one' or 'live-debate'."""

    DEFAULT_CSS = """
    FlowPickerScreen {
        align: left top;
        background: transparent;
    }
    #flow-banner {
        width: 100%;
        height: auto;
        background: $panel-darken-2;
        padding: 0 1;
    }
    #flow-options {
        height: auto;
        width: 100%;
        border: none;
        padding: 0;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "app.quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        with Vertical(id="flow-banner"):
            yield Label("Choose session flow:")
            yield OptionList(
                Option("Pick one  — choose the better response", id="pick-one"),
                Option("Live debate  — watch agents exchange rounds", id="live-debate"),
                id="flow-options",
                compact=True,
            )

    def on_mount(self) -> None:
        # Pre-highlight pick-one (index 0) as the default
        self.query_one("#flow-options", OptionList).highlighted = 0

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(event.option_id)  # Returns "pick-one" or "live-debate"
```

### Pattern 3: y/n Key Binding for Confirm Screens

**What:** `ModalScreen[bool]` with explicit `Binding("y", ...)` and `Binding("n", ...)` that `dismiss(True/False)`.

**When to use:** ConfirmEndDebateScreen (Esc confirm) and ApplyConfirmScreen (write confirm).

```python
# Source: Textual 8 Binding + ModalScreen API (verified via inspection 2026-02-24)
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label
from textual.app import ComposeResult


class ApplyConfirmScreen(ModalScreen[bool]):
    """Confirmation gate before writing files. Returns True to write, False to reject."""

    DEFAULT_CSS = """
    ApplyConfirmScreen {
        align: center middle;
    }
    #confirm-dialog {
        width: 60;
        height: 7;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("y", "confirm", "Write files"),
        Binding("n", "reject", "Cancel"),
        Binding("escape", "reject", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        with Vertical(id="confirm-dialog"):
            yield Label("Apply changes? Press y to write, n to cancel.")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_reject(self) -> None:
        self.dismiss(False)
```

### Pattern 4: asyncio.Event Debate Stop Signal

**What:** An `asyncio.Event` stored on the app drives the debate loop exit. The Esc key handler (via `ConfirmEndDebateScreen`) sets it. The debate worker checks `is_set()` between rounds.

**When to use:** Any time a keypress must signal a running async loop without cancelling the entire worker.

```python
# Source: asyncio.Event stdlib (Python 3.10+)
# In AgentBureauApp:
def on_mount(self) -> None:
    # ... existing init ...
    self._debate_stop: asyncio.Event = asyncio.Event()

# Debate loop in worker:
async def _run_live_debate(self, prompt: str) -> None:
    self._debate_stop.clear()
    max_rounds = 3  # Claude's discretion default

    for round_num in range(1, max_rounds + 1):
        if self._debate_stop.is_set():
            break
        # Post round boundary marker to both panes
        self.post_message(RoundBoundary(round_num=round_num))
        # Stream both agents for this round
        await self._run_one_round(round_num)

    # Transition to pick-winner
    self.post_message(DebateEnded())

# Esc key handler:
def action_end_debate(self) -> None:
    def _on_confirm(confirmed: bool) -> None:
        if confirmed:
            self._debate_stop.set()
    self.push_screen(ConfirmEndDebateScreen(), _on_confirm)
```

### Pattern 5: Code Proposal Extraction

**What:** Parse agent output for fenced code blocks (reuse `content.py` regex patterns) and extract the code content. Optionally detect filename from a comment on the first line.

**When to use:** During reconciliation and code apply — extract agent proposals before generating diff.

```python
# Source: Python stdlib re + existing content.py patterns (verified in codebase)
import re
from dataclasses import dataclass

FENCE_OPEN = re.compile(r'^```(\w+)$')
FENCE_CLOSE = re.compile(r'^```$')
FILE_COMMENT = re.compile(r'^#\s+(\S+\.\w+)$|^//\s+(\S+\.\w+)$')


@dataclass
class CodeProposal:
    language: str
    code: str
    filename: str | None  # None if agent didn't specify a target file


def extract_code_proposals(full_text: str) -> list[CodeProposal]:
    """Extract all fenced code blocks from agent output."""
    proposals = []
    lines = full_text.splitlines()
    i = 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if m:
            language = m.group(1)
            code_lines = []
            i += 1
            filename = None
            while i < len(lines) and not FENCE_CLOSE.match(lines[i]):
                # Check first line for file path comment
                if not code_lines:
                    fm = FILE_COMMENT.match(lines[i])
                    if fm:
                        filename = fm.group(1) or fm.group(2)
                        i += 1
                        continue
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip closing fence
            proposals.append(CodeProposal(language=language, code='\n'.join(code_lines), filename=filename))
        else:
            i += 1
    return proposals
```

### Pattern 6: Unified Diff Generation and Display

**What:** Use `difflib.unified_diff()` to compare agent proposals. Display via `Syntax(diff_text, "diff", theme="monokai")` in `RichLog` (same pattern as code block rendering in `content.py`).

```python
# Source: Python stdlib difflib (verified 2026-02-24) + existing content.py Syntax pattern
import difflib
from rich.syntax import Syntax


def generate_unified_diff(
    a_code: str, b_code: str, fromfile: str = "agent_a", tofile: str = "agent_b"
) -> str:
    """Generate a unified diff between two code strings."""
    a_lines = a_code.splitlines(keepends=True)
    b_lines = b_code.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        a_lines, b_lines,
        fromfile=fromfile,
        tofile=tofile,
    ))
    return ''.join(diff_lines)


def write_diff_to_log(log, diff_text: str) -> None:
    """Write unified diff to RichLog with syntax highlighting."""
    if diff_text.strip():
        log.write(Syntax(diff_text, "diff", theme="monokai", background_color="default"))
    else:
        log.write("[dim]No differences — proposals are identical.[/dim]")
```

### Pattern 7: Atomic File Write

**What:** Write to a temp file in the same directory as the target, then `os.rename()` to the target path. Atomic on POSIX (rename is atomic within the same filesystem).

**When to use:** Any confirmed code apply operation.

```python
# Source: Python stdlib pathlib + tempfile + os (verified 2026-02-24)
import os
import tempfile
from pathlib import Path


def write_file_atomic(target: Path, content: str) -> None:
    """Write content to target path atomically via temp file + rename."""
    target.parent.mkdir(parents=True, exist_ok=True)
    dir_fd = os.open(str(target.parent), os.O_RDONLY)
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.tmp",
            suffix=".tmp",
        )
        try:
            with os.fdopen(tmp_fd, 'w') as f:
                f.write(content)
            os.rename(tmp_path, str(target))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    finally:
        os.close(dir_fd)
```

### Pattern 8: SessionState Extension

**What:** Add Phase 4 states to the existing `SessionState` enum. All existing states remain unchanged (OCP compliance — extend without modifying).

```python
# Source: existing src/tui/session.py + Phase 4 requirements
from enum import Enum, auto


class SessionState(Enum):
    # Phase 3 states (unchanged)
    IDLE = auto()
    STREAMING = auto()
    CLASSIFYING = auto()
    DONE = auto()
    # Phase 4 additions
    FLOW_PICK = auto()       # Waiting for user to choose pick-one or live-debate
    DEBATING = auto()        # Live-debate rounds in progress
    PICK_WINNER = auto()     # Waiting for user to select winner
    RECONCILING = auto()     # Agents producing reconciliation discussion
    CONFIRMING_APPLY = auto() # Showing diff + waiting for y/n
```

### Pattern 9: New Textual Messages for Phase 4

```python
# Source: existing src/tui/messages.py pattern (dataclass + Message)
from dataclasses import dataclass
from textual.message import Message


@dataclass
class RoundBoundary(Message):
    """Signals a new debate round — triggers divider line in both panes."""
    round_num: int


@dataclass
class DebateEnded(Message):
    """Signals debate rounds complete — triggers pick-winner screen."""
    pass


@dataclass
class ReconciliationReady(Message):
    """Reconciliation text + diff ready for display in ReconciliationPanel."""
    discussion_text: str      # Plain-language agent discussion
    diff_text: str            # Unified diff for code changes
    agreed_code: str          # Final agreed code block (for apply)
    language: str             # Programming language for syntax highlight


@dataclass
class ApplyResult(Message):
    """User confirmed or rejected file write."""
    confirmed: bool
    files_written: list[str]  # Paths of successfully written files (empty if rejected)
```

### Anti-Patterns to Avoid

- **Calling push_screen without wait_for_dismiss from outside a worker:** Raises `NoActiveWorker`. Only use `wait_for_dismiss=True` inside a worker coroutine, or use the callback form (`push_screen(screen, callback)`) from synchronous handlers.
- **Writing files from inside a worker without posting to app first:** Worker should post `ReconciliationReady`, app handler pushes `ApplyConfirmScreen`, then calls apply logic. Never write files directly from a worker.
- **Using Worker.cancel() for debate stop:** Cancel is abrupt and may leave subprocesses running. Use `asyncio.Event` instead — the debate loop exits cleanly after the current round.
- **Checking `_debate_stop` inside `_stream_pty/_stream_pipe`:** These are reused from Phase 3. Do not modify them. Check `_debate_stop` only between rounds in the debate loop.
- **Single-file import for `Option`:** In Textual 8, `Option` lives in `textual.widgets._option_list`, not `textual.widgets`. Use `from textual.widgets._option_list import OptionList, Option`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Diff generation | Custom line comparison | `difflib.unified_diff()` | Handles context lines, file headers, edge cases; stdlib |
| Arrow+Enter menu navigation | Custom key handler in Screen | `OptionList` with Option items | Built-in up/down/enter bindings; auto-highlights first item |
| Awaiting modal result from worker | asyncio.Future manually | `push_screen(wait_for_dismiss=True)` | Textual manages the future; raises on misuse |
| File write safety | Manual backup/restore | temp file + `os.rename()` | POSIX atomic; prevents partial writes |
| Debate stop signaling | Worker.cancel() | `asyncio.Event` | Graceful exit; worker cleans up subprocesses properly |

**Key insight:** All interactive patterns (modal screens, key navigation, async modal-then-continue) are already solved by Textual 8 — use them exactly as documented.

---

## Common Pitfalls

### Pitfall 1: push_screen wait_for_dismiss Called Outside Worker
**What goes wrong:** `NoActiveWorker` exception crashes the app or is silently swallowed.
**Why it happens:** `push_screen(wait_for_dismiss=True)` requires Textual's internal worker context to manage the Future. Calling it from a regular `on_*` handler or `action_*` method has no active worker.
**How to avoid:** Always call `push_screen(wait_for_dismiss=True)` from within a coroutine passed to `run_worker()`. Use the callback form `push_screen(screen, callback)` from synchronous handlers.
**Warning signs:** `NoActiveWorker` in logs; modal appears but worker never resumes.

### Pitfall 2: OptionList Option Import Path
**What goes wrong:** `ImportError: cannot import name 'Option' from 'textual.widgets'`
**Why it happens:** In Textual 8, `Option` is in `textual.widgets._option_list`, not the public `textual.widgets` namespace.
**How to avoid:** `from textual.widgets._option_list import OptionList, Option`
**Warning signs:** Import error at module load time.

### Pitfall 3: Debate Stop Event Not Cleared Between Sessions
**What goes wrong:** The second debate session stops immediately because `_debate_stop` is still set from the previous session.
**Why it happens:** `asyncio.Event` retains its state; `set()` persists until `clear()` is called.
**How to avoid:** Call `self._debate_stop.clear()` at the start of every new `_run_live_debate()` call. Also call it in `_start_session()` reset block.
**Warning signs:** Second live-debate session ends before showing any rounds.

### Pitfall 4: ModalScreen Without Escape/Ctrl-C Binding
**What goes wrong:** User is trapped in a modal screen; Ctrl-C quits the whole app instead of dismissing.
**Why it happens:** `ModalScreen` does not define Escape or Ctrl-C bindings by default (verified in Textual 8). Ctrl-C is intercepted by the app-level priority binding that pushes `QuitScreen`.
**How to avoid:** Add `Binding("ctrl+c", "app.quit", priority=True)` to `FlowPickerScreen` (as per CONTEXT.md — Ctrl-C quits from flow picker). For other modals, add `Binding("escape", "reject", "Cancel")`.
**Warning signs:** User cannot exit a modal with keyboard.

### Pitfall 5: Unified Diff on Non-Newline-Terminated Lines
**What goes wrong:** Diff output has messy `\ No newline at end of file` markers or missing diff hunks.
**Why it happens:** `difflib.unified_diff()` expects lines with `\n`. Lines from `splitlines()` don't have trailing newlines unless `keepends=True` is used.
**How to avoid:** Use `a_code.splitlines(keepends=True)` when splitting code for diff. If code doesn't end with `\n`, append it before splitting.
**Warning signs:** Diff output ends with `\ No newline at end of file`; diff hunks appear malformed.

### Pitfall 6: Atomic Write Across Filesystems
**What goes wrong:** `os.rename()` raises `OSError: [Errno 18] Invalid cross-device link`
**Why it happens:** `os.rename()` is atomic only within the same filesystem. If the temp file is on a different filesystem (e.g., `/tmp` vs project dir), it fails.
**How to avoid:** Always create the temp file in the **same directory** as the target file (`dir=target.parent` in `tempfile.mkstemp()`).
**Warning signs:** `OSError` on rename during apply.

### Pitfall 7: Reconciliation Agent Prompt Confusion
**What goes wrong:** Agents in reconciliation round produce code that's worse than their originals, or they start debating again instead of converging.
**Why it happens:** If the reconciliation prompt is adversarial ("which approach is better") rather than collaborative ("what is the best unified solution"), agents compete rather than merge.
**How to avoid:** Frame reconciliation prompt as: "Here is what Agent A proposed: [A's code]. Here is what Agent B proposed: [B's code]. These are complementary perspectives. Produce the best unified solution that incorporates the strengths of both. Reply with only the final code."
**Warning signs:** Reconciliation output is much longer than either original; contains hedging language like "on the other hand".

---

## Code Examples

### Flow-Picker Screen (Full Implementation Shape)

```python
# Source: Textual 8 ModalScreen + OptionList APIs (verified 2026-02-24)
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets._option_list import Option


class FlowPickerScreen(ModalScreen[str]):
    """Top-banner flow selection. Returns 'pick-one' or 'live-debate'."""

    DEFAULT_CSS = """
    FlowPickerScreen {
        align: left top;
        background: rgba(0, 0, 0, 0);
    }
    #banner {
        width: 100%;
        height: auto;
        background: $panel-darken-2;
        padding: 0 1;
    }
    #flow-options {
        width: 100%;
        height: auto;
        border: none;
        padding: 0;
    }
    """

    BINDINGS = [Binding("ctrl+c", "app.quit", "Quit", priority=True)]

    def compose(self) -> ComposeResult:
        with Vertical(id="banner"):
            yield Label("Choose session flow  (arrow keys + Enter):")
            yield OptionList(
                Option("  Pick one   — select the better response after both finish", id="pick-one"),
                Option("  Live debate — watch agents exchange rounds in real time", id="live-debate"),
                id="flow-options",
                compact=True,
            )

    def on_mount(self) -> None:
        ol = self.query_one("#flow-options", OptionList)
        ol.focus()
        ol.highlighted = 0  # pre-highlight pick-one

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option_id)
```

### Debate Round Loop (Structural Pattern)

```python
# Inside AgentBureauApp, called from _run_session worker
async def _run_live_debate(self, prompt: str) -> None:
    """Run up to max_rounds of debate, stopping early if _debate_stop is set."""
    from tui.bridge import _stream_pty, _stream_pipe, _pty_available, CLAUDE, CODEX
    import asyncio

    self._debate_stop.clear()
    MAX_ROUNDS = 3  # Claude's discretion default

    stream_fn = _stream_pty if _pty_available() else _stream_pipe
    last_claude = ""
    last_codex = ""

    for round_num in range(1, MAX_ROUNDS + 1):
        if self._debate_stop.is_set():
            break

        # Post round boundary divider to both panes
        self.post_message(RoundBoundary(round_num=round_num))

        # Build per-agent context prompts for rounds 2+
        if round_num == 1:
            claude_prompt = prompt
            codex_prompt = prompt
        else:
            claude_prompt = (
                f"Original task: {prompt}\n\n"
                f"The other agent responded:\n{last_codex}\n\n"
                f"Refine your approach based on this. Be concise."
            )
            codex_prompt = (
                f"Original task: {prompt}\n\n"
                f"The other agent responded:\n{last_claude}\n\n"
                f"Refine your approach based on this. Be concise."
            )

        q: asyncio.Queue = asyncio.Queue()
        task_a = asyncio.create_task(stream_fn(CLAUDE, claude_prompt, 60.0, q))
        task_b = asyncio.create_task(stream_fn(CODEX, codex_prompt, 60.0, q))

        collected: dict[str, list[str]] = {"claude": [], "codex": []}
        terminal_count = 0
        while terminal_count < 2:
            event = await q.get()
            if event.type == "token":
                self.post_message(TokenReceived(agent=event.agent, text=event.text))
                collected[event.agent].append(event.text)
            elif event.type in ("done", "error", "timeout"):
                self.post_message(AgentFinished(agent=event.agent, event=event))
                terminal_count += 1

        await asyncio.gather(task_a, task_b)
        last_claude = "\n".join(collected["claude"])
        last_codex = "\n".join(collected["codex"])

    self.post_message(DebateEnded())
    self._last_texts = {"claude": last_claude, "codex": last_codex}
```

### ReconciliationPanel Widget

```python
# Source: textual.widgets.RichLog + rich.syntax.Syntax (verified existing pattern)
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, RichLog
from rich.syntax import Syntax


class ReconciliationPanel(Widget):
    """Below-panes panel showing agent reconciliation discussion and diff.

    Hidden (display=False) until ReconciliationReady message arrives.
    """

    DEFAULT_CSS = """
    ReconciliationPanel {
        height: 15;
        border-top: solid $border;
        display: none;
    }
    ReconciliationPanel #recon-header {
        height: 1;
        background: $panel-darken-1;
        content-align: left middle;
        padding: 0 1;
    }
    ReconciliationPanel #recon-log {
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Reconciliation", id="recon-header")
        yield RichLog(id="recon-log", highlight=True, markup=True)

    def show_reconciliation(self, discussion: str, diff_text: str) -> None:
        """Display reconciliation discussion and diff."""
        self.display = True
        log = self.query_one("#recon-log", RichLog)
        log.clear()
        if discussion:
            log.write(discussion)
        if diff_text.strip():
            log.write(Syntax(diff_text, "diff", theme="monokai", background_color="default"))
        else:
            log.write("[dim]No code differences detected.[/dim]")
```

### Apply Logic (Module-Level Function)

```python
# Source: Python stdlib pathlib + tempfile + os (verified 2026-02-24)
# In src/tui/apply.py
import os
import tempfile
from pathlib import Path


def write_file_atomic(target: Path, content: str) -> None:
    """Write content to target atomically (temp file + rename)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            f.write(content)
        os.rename(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Modal confirmation with Button widgets | ModalScreen with Binding("y") / Binding("n") | Textual 8 | Keyboard-only navigation, no mouse required |
| Polling loops for modal results | `push_screen(wait_for_dismiss=True)` from worker | Textual 0.40+ | Clean async suspension; no manual Future management |
| `diff` subprocess for code diff | `difflib.unified_diff()` stdlib | N/A | No subprocess overhead; deterministic; no PATH dependency |

---

## Open Questions

1. **Reconciliation when agents can't converge**
   - What we know: Agents sometimes produce outputs that differ in fundamental approach, not just implementation detail. The CONTEXT.md says "how partial/failed reconciliation is handled" is Claude's discretion.
   - What's unclear: Should the ReconciliationPanel show both proposals side-by-side if agents can't agree, or show only one? Should there be a second round of reconciliation?
   - Recommendation: Define a reconciliation timeout (30s per agent). If agents produce outputs with >80% diff by line (using `difflib.SequenceMatcher.ratio()`), show both proposals in the panel with a "[agents could not fully agree — showing both]" header. User still picks via ApplyConfirmScreen with y/n.

2. **Code block filename extraction reliability**
   - What we know: Agents don't always prefix their code blocks with a filename comment. The `FILE_COMMENT` regex pattern only works if agent uses `# path/to/file.py` as the first line.
   - What's unclear: When no filename is detected, what is the target path for apply?
   - Recommendation: When no filename detected, show diff with a `[filename unknown]` placeholder and disable file write — show user only the code to manually copy. This prevents writing to wrong paths. Keep this simple for Phase 4; filename detection can be improved in v2.

3. **Max rounds default validation**
   - What we know: 3 total rounds (1 initial + 2 debate) is recommended by this research. This is Claude's discretion.
   - What's unclear: Whether agents in round 2-3 actually improve their proposals vs. just restating them.
   - Recommendation: Default `MAX_ROUNDS = 3`. Make it a module constant in `app.py` so it can be changed without touching logic.

---

## Sources

### Primary (HIGH confidence)
- Textual 8 source inspection via `python -c "import inspect; ..."` in installed `.venv` (2026-02-24) — `ModalScreen`, `OptionList`, `Option`, `push_screen`, `run_worker`, `Worker.cancel`, `Screen.BINDINGS`
- Python 3.14 stdlib `difflib.unified_diff` help (2026-02-24)
- Python stdlib `tempfile.mkstemp` + `os.rename` (2026-02-24)
- Existing codebase `src/tui/app.py`, `src/tui/session.py`, `src/tui/messages.py`, `src/tui/bridge.py`, `src/tui/content.py`, `src/tui/widgets/quit_screen.py` — patterns confirmed working in Phase 3

### Secondary (MEDIUM confidence)
- `asyncio.Event` cooperative stop pattern — stdlib; pattern verified with working test in REPL (2026-02-24)
- `Syntax(text, "diff", theme="monokai")` for diff rendering — `rich` library bundled with Textual; tested in REPL

### Tertiary (LOW confidence)
- Reconciliation prompt design (collaborative vs adversarial framing) — based on reasoning about LLM behavior; not empirically tested in this project

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via direct inspection of installed packages
- Architecture: HIGH — all patterns verified via REPL tests against installed Textual 8.0.0
- Pitfalls: HIGH — most derived from actual code inspection (e.g., Option import path, wait_for_dismiss constraint)
- Reconciliation prompt: LOW — reasoning-based, not empirically validated

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (Textual 8.x is stable; stdlib patterns don't change)
