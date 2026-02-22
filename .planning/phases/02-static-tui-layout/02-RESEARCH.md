# Phase 2: Static TUI Layout - Research

**Researched:** 2026-02-21
**Domain:** Textual (Python TUI framework) — layout, scrolling, keyboard navigation, syntax highlighting
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Column layout**
- 50/50 horizontal split — each agent pane gets equal width
- Columns separated by a single vertical line divider (box-drawing character, full height)
- Each column header shows agent name only (e.g., "claude", "codex") — clean and minimal
- Empty pane shows dimmed placeholder text (e.g., "Waiting for claude...") centered in the pane area

**Keyboard navigation**
- Left/right arrow keys switch focus between the left and right pane
- Up/down arrow keys scroll the currently focused pane line by line
- Active pane indicated by a highlighted (brighter) agent name header; inactive header is dimmed
- Exit: `q` exits cleanly; Ctrl-C shows a confirmation prompt before exiting

**Syntax highlighting**
- Code detection: fenced code blocks only (triple-backtick with language tag: ```python, ```js, etc.)
- Language support: detect from the language tag in the code fence — highlight whatever language is tagged
- Visual style: code blocks have a slightly dimmed background to visually separate them from prose text; code appears inset within the pane flow
- Inline code (single backticks): Claude's Discretion

### Claude's Discretion
- Inline code styling (single backticks) — Claude picks what looks cleanest
- Exact color values and theme (dark terminal assumed; color palette is open)
- Exact placeholder text wording for empty panes
- Page Up/Down support as a bonus scroll shortcut (arrow keys are required minimum)
- Scrollback buffer size (must be bounded — no OOM)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TUI-01 | User sees agent responses displayed side-by-side in columnar panes, one column per agent | Textual `Horizontal` container with `width: 1fr` gives equal 50/50 split automatically |
| TUI-02 | Each pane is labeled with the agent's name (e.g., "claude", "codex") | Static label widget docked at top of each pane column; styled via `:focus` pseudo-class for active/inactive |
| TUI-04 | Each pane is independently scrollable with bounded scrollback (no OOM) | `RichLog(max_lines=N)` implements bounded circular buffer; each pane has its own RichLog |
| TUI-05 | Code blocks in agent output are syntax-highlighted | `rich.syntax.Syntax` object written to `RichLog`; detect fenced blocks in incoming text, extract language tag |
| TUI-06 | Layout adapts to terminal width (80 / 120 / wide column breakpoints) | `width: 1fr` units in Textual CSS respond automatically to terminal resize; no explicit breakpoint code needed |
| TUI-07 | User can navigate the TUI entirely by keyboard (scroll, pick, exit) | `BINDINGS` class variable maps arrow keys and q; `widget.focus()` switches active pane programmatically |
| TUI-08 | User can exit at any time with Ctrl-C or q without corrupting state or leaving zombie processes | `q` → `self.exit()`; Ctrl-C → push `ModalScreen[bool]` confirmation; Textual handles terminal cleanup on exit |
</phase_requirements>

---

## Summary

Textual is the locked framework choice for this project. As of February 2026, Textual is at version **8.0.0** — not the `<1.0` range mentioned in the roadmap decision log. The project's `pyproject.toml` currently lists no runtime dependencies at all; Textual must be added. The correct pin is `>=0.80.0,<9` to stay on the current major version while avoiding unknown breaking changes in a hypothetical v9.

The core layout pattern for this phase is: one `App` containing a `Horizontal` container, which holds two column containers — each a `VerticalScroll` wrapping a `RichLog`. A one-character-wide `Static` widget between them renders the vertical divider. Each column's header (agent name) is a `Label` docked inside the column. The `RichLog.max_lines` parameter bounds the scrollback buffer. Left/right arrow key bindings call `widget.focus()` to switch active pane. The active pane header is styled via the `:focus` pseudo-class in Textual CSS. Syntax highlighting uses `rich.syntax.Syntax` objects written to `RichLog.write()`, with inline parsing of fenced code blocks.

Textual provides a headless `Pilot` test harness (`app.run_test()`) that works with `pytest-asyncio` — already configured in the project. All TUI behavior can be tested without a real terminal. The one area requiring design care is parsing fenced code blocks from incoming text lines: this must be done in application code (Textual does not parse markdown in RichLog). The `Markdown` widget does parse markdown automatically but is harder to bound for scrollback; `RichLog` + manual fence detection is the recommended approach.

**Primary recommendation:** Use `RichLog(max_lines=5000)` per pane, parse fenced code blocks in `AgentPane` widget code, write `Syntax` objects for code and plain text for prose. Use `Horizontal` / `VerticalScroll` layout with `width: 1fr`. Test everything with Textual's Pilot.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.0.0 (latest) | TUI application framework | Locked project choice; asyncio-native; chosen in Phase 1 planning |
| rich | >=14.2.0 (transitive via textual) | Terminal rendering, Syntax objects | Textual's rendering engine; provides `Syntax` class for code highlighting |
| pygments | ^2.19.2 (transitive via textual) | Code syntax highlighting | Rich's highlighting backend; supports 500+ languages via fence tags |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | >=0.25,<2.0 (already pinned) | Async test runner | All Textual Pilot tests are async coroutines |
| pytest-textual-snapshot | latest | Visual regression testing | Optional: snapshot tests for layout validation across terminal sizes |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| RichLog (per-pane, manual fence parse) | Markdown widget | Markdown auto-parses fenced blocks but bounded scrollback requires custom work; RichLog has `max_lines` built in |
| VerticalScroll wrapping RichLog | Custom ScrollView | Custom ScrollView requires implementing `render_line()` and virtual sizing; far more complex for no gain |
| Textual CSS (TCSS) inline string | External .tcss file | Inline `CSS = """..."""` is simpler for a single-module layout; external file better when CSS grows large |

**Installation:**
```bash
pip install "textual>=0.80.0,<9"
```

Note: `rich` and `pygments` are installed automatically as Textual dependencies. No separate install needed.

Add to `pyproject.toml` `[project]` `dependencies`:
```toml
dependencies = [
    "textual>=0.80.0,<9",
]
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/
└── tui/
    ├── __init__.py          # existing — "tui package" comment
    ├── bridge.py            # existing Phase 1 — async streaming bridge
    ├── event_bus.py         # existing Phase 1 — typed BridgeEvent types
    ├── app.py               # NEW — AgentBureauApp(App) Textual application
    ├── widgets/
    │   ├── __init__.py      # NEW — widget package init
    │   ├── agent_pane.py    # NEW — AgentPane widget (VerticalScroll + RichLog + header)
    │   └── quit_screen.py   # NEW — QuitScreen(ModalScreen[bool]) confirmation dialog
    └── styles.tcss          # NEW — Textual CSS (TCSS) for layout and theming
tests/
└── tui/
    ├── test_app.py          # NEW — Pilot-based layout and navigation tests
    ├── test_agent_pane.py   # NEW — AgentPane unit tests (write, scroll, highlight)
    └── test_quit_screen.py  # NEW — QuitScreen tests
```

### Pattern 1: Horizontal 50/50 Split with Divider

**What:** `Horizontal` container with two `AgentPane` columns and a one-column `Static` divider between them.
**When to use:** The root layout of the app — compose once, never change structure.

```python
# Source: https://textual.textualize.io/guide/layout/
from textual.app import App, ComposeResult
from textual.containers import Horizontal

class AgentBureauApp(App):
    CSS = """
    Screen {
        background: $surface;
    }

    Horizontal {
        height: 100%;
    }

    #divider {
        width: 1;
        height: 100%;
        background: $panel;
    }

    AgentPane {
        width: 1fr;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield AgentPane(agent_name="claude", id="pane-left")
            yield Static("", id="divider")
            yield AgentPane(agent_name="codex", id="pane-right")
```

### Pattern 2: AgentPane Widget (VerticalScroll + RichLog + Header)

**What:** A custom widget that composes a docked header (agent name) and a scrollable `RichLog` for content.
**When to use:** Each agent column. Must be focusable and independently scrollable.

```python
# Source: https://textual.textualize.io/guide/widgets/
# Source: https://textual.textualize.io/widgets/rich_log/
from textual.widget import Widget
from textual.widgets import Label, RichLog
from textual.app import ComposeResult

SCROLLBACK_LIMIT = 5000  # bounded — no OOM

class AgentPane(Widget):
    can_focus = True

    DEFAULT_CSS = """
    AgentPane {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }

    AgentPane #header {
        height: 1;
        background: $panel-darken-1;
        color: $text-muted;
        content-align: center middle;
        padding: 0 1;
    }

    AgentPane:focus #header {
        background: $accent;
        color: $text;
    }

    AgentPane #content {
        height: 1fr;
    }

    AgentPane #placeholder {
        color: $text-disabled;
        content-align: center middle;
        height: 1fr;
    }
    """

    def __init__(self, agent_name: str, **kwargs) -> None:
        self.agent_name = agent_name
        self._has_content = False
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Label(self.agent_name, id="header")
        yield Label(f"Waiting for {self.agent_name}...", id="placeholder")
        yield RichLog(
            id="content",
            highlight=True,
            markup=False,
            max_lines=SCROLLBACK_LIMIT,
            auto_scroll=True,
        )

    def on_mount(self) -> None:
        # Hide content log until first write
        self.query_one("#content").display = False
```

### Pattern 3: Keyboard Navigation (Left/Right Focus, Up/Down Scroll)

**What:** App-level BINDINGS for left/right pane switching; pane-level BINDINGS for up/down scroll.
**When to use:** The locked navigation spec: arrows control both pane focus and scrolling.

```python
# Source: https://textual.textualize.io/guide/input/
from textual.app import App
from textual.binding import Binding

class AgentBureauApp(App):
    BINDINGS = [
        Binding("left", "focus_left", "Focus left pane", show=False),
        Binding("right", "focus_right", "Focus right pane", show=False),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "confirm_quit", "Exit", priority=True),
    ]

    def action_focus_left(self) -> None:
        self.query_one("#pane-left").focus()

    def action_focus_right(self) -> None:
        self.query_one("#pane-right").focus()

    def action_quit(self) -> None:
        self.exit()

    def action_confirm_quit(self) -> None:
        self.push_screen(QuitScreen(), self._handle_quit_result)

    def _handle_quit_result(self, result: bool | None) -> None:
        if result:
            self.exit()
```

For up/down scrolling, bind inside `AgentPane`:
```python
# Source: https://textual.textualize.io/guide/input/
class AgentPane(Widget):
    BINDINGS = [
        Binding("up", "scroll_up", "Scroll up", show=False),
        Binding("down", "scroll_down", "Scroll down", show=False),
        Binding("pageup", "scroll_page_up", "Page up", show=False),
        Binding("pagedown", "scroll_page_down", "Page down", show=False),
    ]

    def action_scroll_up(self) -> None:
        self.query_one(RichLog).scroll_up(animate=False)

    def action_scroll_down(self) -> None:
        self.query_one(RichLog).scroll_down(animate=False)
```

### Pattern 4: ModalScreen Confirmation Exit Dialog

**What:** Ctrl-C pushes a `ModalScreen[bool]` asking "Quit?". Dismissing with True exits.
**When to use:** Locked requirement — Ctrl-C must show confirmation before exit.

```python
# Source: https://textual.textualize.io/guide/screens/
from textual.screen import ModalScreen
from textual.containers import Grid
from textual.widgets import Button, Label

class QuitScreen(ModalScreen[bool]):
    CSS = """
    QuitScreen {
        align: center middle;
    }

    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: thick $background 80%;
        background: $surface;
    }

    #question {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center bottom;
    }
    """

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "quit")
```

### Pattern 5: Syntax Highlighting via RichLog + rich.syntax.Syntax

**What:** Parse incoming text for fenced code blocks; write `Syntax` objects for code, plain text for prose.
**When to use:** Every `write_line()` call to a pane — Phase 2 uses static placeholder content so the parsing runs on pre-loaded fixture text.

```python
# Source: https://github.com/Textualize/textual/blob/main/docs/examples/widgets/rich_log.py
# Source: https://textual.textualize.io/widgets/rich_log/
import re
from rich.syntax import Syntax
from textual.widgets import RichLog

FENCE_OPEN = re.compile(r"^```(\w+)$")
FENCE_CLOSE = re.compile(r"^```$")

def write_content_to_pane(log: RichLog, text: str) -> None:
    """
    Write markdown-like text to a RichLog.
    Fenced code blocks are rendered as Syntax objects (syntax highlighted).
    All other lines are written as plain text.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = FENCE_OPEN.match(line)
        if m:
            language = m.group(1)
            code_lines = []
            i += 1
            while i < len(lines) and not FENCE_CLOSE.match(lines[i]):
                code_lines.append(lines[i])
                i += 1
            code = "\n".join(code_lines)
            log.write(
                Syntax(
                    code,
                    language,
                    theme="monokai",
                    indent_guides=True,
                    background_color="default",  # slightly dimmed via theme
                )
            )
        else:
            if line.strip():
                log.write(line)
        i += 1
```

**Inline code (Claude's Discretion):** Use Rich markup: wrap single-backtick content in `[bold cyan]...[/bold cyan]` before writing. This is lightweight and stays consistent with the dark terminal theme without requiring a full markdown parser.

### Pattern 6: Testing with Pilot

**What:** Headless `run_test()` context manager + `Pilot` for simulating key presses and asserting widget state.
**When to use:** All tests for layout, keyboard navigation, and content rendering.

```python
# Source: https://textual.textualize.io/guide/testing/
import pytest
from tui.app import AgentBureauApp
from tui.widgets.agent_pane import AgentPane

@pytest.mark.asyncio
async def test_left_pane_focused_on_startup():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        left_pane = app.query_one("#pane-left")
        assert left_pane == app.focused

@pytest.mark.asyncio
async def test_right_arrow_switches_focus():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("right")
        right_pane = app.query_one("#pane-right")
        assert right_pane == app.focused

@pytest.mark.asyncio
async def test_layout_at_80_columns():
    app = AgentBureauApp()
    async with app.run_test(size=(80, 24)) as pilot:
        left = app.query_one("#pane-left")
        right = app.query_one("#pane-right")
        # Each pane should be roughly half of 79 usable columns
        assert left.size.width > 30
        assert right.size.width > 30
```

### Anti-Patterns to Avoid

- **Global `up`/`down` bindings in App:** Arrow keys must be captured by the focused pane, not the App. Bind `up`/`down` in `AgentPane`, not in `AgentBureauApp`. App-level bindings fire before widget-level ones only when `priority=True`.
- **Unbounded RichLog:** Never create `RichLog()` without `max_lines=N`. Long-running sessions will accumulate lines until OOM. Use `max_lines=5000`.
- **`Markdown` widget for bounded panes:** `Markdown` is a container widget with no built-in line-count limit. Use `RichLog` with manual fence parsing instead.
- **`can_focus=False` on AgentPane:** Without `can_focus = True`, `widget.focus()` silently does nothing and arrow-key pane switching breaks completely.
- **Nesting VerticalScroll inside AgentPane that is already scrollable:** Don't add `VerticalScroll` as a child of `AgentPane` if `AgentPane` itself handles layout — let `RichLog` handle its own internal scrolling via `scroll_up()` / `scroll_down()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal rendering engine | Custom ANSI renderer | `textual` + `rich` | Handles 256/truecolor, Unicode, window resize, mouse, focus — hundreds of edge cases |
| Syntax highlighting | Regex-based tokenizer | `rich.syntax.Syntax` + pygments | Supports 500+ languages; handles edge cases (nested strings, multiline tokens, escape sequences) |
| Bounded circular buffer | `deque(maxlen=N)` in widget | `RichLog(max_lines=N)` | RichLog implements the trim logic internally and recalculates scroll position correctly |
| Modal dialog | Custom overlay widget | `textual.screen.ModalScreen` | Textual handles focus trapping, background dimming, screen stack, and dismiss callbacks |
| Terminal cleanup on exit | `atexit` + signal handlers | `App.exit()` | Textual resets terminal state (alternate screen, cursor) atomically on exit |
| Key binding dispatch | `on_key()` conditional chain | `BINDINGS` + `action_*()` | Textual's binding system handles priority, focus chain traversal, and Footer display automatically |

**Key insight:** The Rich + Textual stack is purpose-built for exactly this use case. Every piece of custom code in these areas replicates already-solved problems with worse edge-case handling.

---

## Common Pitfalls

### Pitfall 1: Version Constraint Mismatch

**What goes wrong:** The roadmap decision log says "pin >=0.70.0,<1.0" but Textual is now at **8.0.0**. The `<1.0` upper bound would make pip resolve to an ancient pre-1.0 alpha release (if any exist matching) or fail to install entirely.
**Why it happens:** Textual skipped from 0.x to 1.0 to 8.0 rapidly; the roadmap decision predates this.
**How to avoid:** Pin as `"textual>=0.80.0,<9"` in `pyproject.toml` `[project] dependencies`. This locks to the current major version (8.x) and excludes a hypothetical breaking v9.
**Warning signs:** `pip install textual` succeeds but version is unexpected; import errors for widgets that didn't exist in 0.x.

### Pitfall 2: Arrow Key Binding Conflicts

**What goes wrong:** If `up`/`down` arrows are bound at the App level (not the widget level), they fire regardless of which widget is focused. This either (a) scrolls both panes simultaneously or (b) the App catches the key before the pane ever sees it.
**Why it happens:** App-level BINDINGS intercept keys before widget-level BINDINGS when `priority=True`; even without priority, the routing depends on focus chain position.
**How to avoid:** Define `up`/`down` BINDINGS inside `AgentPane`, not `AgentBureauApp`. Only `left`/`right` (for pane switching) and `q`/`ctrl+c` (app-wide) belong in App bindings.
**Warning signs:** Both panes scroll when pressing up/down; one pane scrolls the other; scroll stops working when a non-pane widget gains focus.

### Pitfall 3: `tests/tui/__init__.py` Shadows `src/tui/`

**What goes wrong:** Creating `tests/tui/__init__.py` causes pytest's sys.path resolution to shadow `src/tui/`. Imports of `tui.app` etc. break.
**Why it happens:** Documented in project STATE.md from Phase 1 finding `[01-02]`.
**How to avoid:** Do NOT create `tests/tui/__init__.py`. Leave it absent. The `pythonpath = ["src"]` pytest config handles import resolution.
**Warning signs:** `ModuleNotFoundError: No module named 'tui.app'` in tests despite the file existing.

### Pitfall 4: Ctrl-C Not Triggering ModalScreen

**What goes wrong:** There is a known Textual issue where `ctrl+c` does not trigger a pushed ModalScreen when another ModalScreen is already on the stack.
**Why it happens:** GitHub issue #5474 — Ctrl-C key binding is swallowed before reaching the handler when modal is active.
**How to avoid:** The `priority=True` binding in the App's `BINDINGS` for `ctrl+c` intercepts before modal. In Phase 2 (static layout only, no nested modals), this is not a concern. For Phase 4 (flow picker modals), revisit this.
**Warning signs:** Ctrl-C does nothing or immediately exits without showing the dialog.

### Pitfall 5: RichLog Scrolling vs VerticalScroll Container Scrolling

**What goes wrong:** If `AgentPane` is placed inside a `VerticalScroll`, pressing up/down may scroll the *container* rather than the *RichLog inside it*.
**Why it happens:** `VerticalScroll` has its own BINDINGS for `up`/`down` that fire before the inner widget's bindings.
**How to avoid:** Do not wrap `AgentPane` in `VerticalScroll`. Let the `Horizontal` container hold `AgentPane` directly. Inside `AgentPane`, scroll the `RichLog` programmatically via `scroll_up()`/`scroll_down()` methods in response to key bindings.
**Warning signs:** Scrolling jumps in large increments, or scrolling has no effect on `RichLog` content.

### Pitfall 6: Focus Not Set on Startup

**What goes wrong:** No pane is focused when the app opens. Arrow keys do nothing until the user presses Tab.
**Why it happens:** Textual focuses the first focusable widget automatically, but only if `can_focus=True` is set AND the widget is traversable in the focus chain.
**How to avoid:** Override `on_mount()` in `AgentBureauApp` to explicitly call `self.query_one("#pane-left").focus()` after compose.
**Warning signs:** Arrow keys have no effect at startup; no pane header appears highlighted.

---

## Code Examples

Verified patterns from official sources:

### Complete AgentBureauApp skeleton

```python
# Source: https://textual.textualize.io/tutorial/ and https://textual.textualize.io/guide/input/
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static

from tui.widgets.agent_pane import AgentPane
from tui.widgets.quit_screen import QuitScreen

class AgentBureauApp(App):
    CSS = """
    Screen { background: $surface; }
    Horizontal { height: 100%; }
    #divider { width: 1; height: 100%; background: $panel; }
    AgentPane { width: 1fr; height: 100%; }
    """

    BINDINGS = [
        Binding("left", "focus_left", "Left pane", show=False),
        Binding("right", "focus_right", "Right pane", show=False),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "confirm_quit", "Exit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield AgentPane(agent_name="claude", id="pane-left")
            yield Static("│", id="divider")
            yield AgentPane(agent_name="codex", id="pane-right")

    def on_mount(self) -> None:
        self.query_one("#pane-left").focus()

    def action_focus_left(self) -> None:
        self.query_one("#pane-left").focus()

    def action_focus_right(self) -> None:
        self.query_one("#pane-right").focus()

    def action_quit(self) -> None:
        self.exit()

    def action_confirm_quit(self) -> None:
        self.push_screen(QuitScreen(), lambda result: self.exit() if result else None)
```

### RichLog write with syntax highlighting

```python
# Source: https://github.com/Textualize/textual/blob/main/docs/examples/widgets/rich_log.py
from rich.syntax import Syntax
from textual.widgets import RichLog

# Write highlighted Python code block
log = self.query_one(RichLog)
log.write(Syntax("def hello():\n    print('world')", "python", theme="monokai"))

# Write plain prose
log.write("This is regular text output from the agent.")
```

### Pilot test for pane switching

```python
# Source: https://textual.textualize.io/guide/testing/
import pytest
from tui.app import AgentBureauApp

@pytest.mark.asyncio
async def test_arrow_key_switches_pane():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.focused.id == "pane-left"
        await pilot.press("right")
        await pilot.pause()
        assert app.focused.id == "pane-right"
        await pilot.press("left")
        await pilot.pause()
        assert app.focused.id == "pane-left"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Textual `<1.0` (alpha series) | Textual 8.0.0 (stable) | 2024-2026 | APIs are stable; many widgets were renamed or redesigned between 0.x and 8.x — do not use 0.x examples |
| `RichLog.write(Markdown(...))` | `RichLog.write(Syntax(...))` for code + plain text for prose | Current | `Markdown` widget in RichLog was never supported; use `Syntax` objects directly |
| Textual company (Textualize) backing | Community open-source | May 2025 | Company shut down but Textual continues; Rich + Textual maintained by Will McGugan as community projects; no abandonment risk |
| `Select.BLANK` | `Select.NULL` | Textual 8.0.0 | Renamed to avoid conflict with `Widget.BLANK` — only relevant if using Select widget |

**Deprecated/outdated:**
- `Markdown.code_dark_theme`, `Markdown.code_light_theme`, `Markdown.code_indent_guides`: Removed from Markdown widget — do not reference these.
- `>=0.70.0,<1.0` pin: This version range does not contain Textual 8.0.0. Must update to `>=0.80.0,<9`.

---

## Open Questions

1. **Exact `max_lines` value for scrollback bound**
   - What we know: `RichLog(max_lines=N)` trims older lines when N is exceeded; no OOM after that
   - What's unclear: What N is appropriate for this use case? Agent responses may be very long or very short
   - Recommendation: Use `max_lines=5000` as the default. At ~100 chars/line average, this is ~500KB per pane — negligible. Expose as a constant `SCROLLBACK_LIMIT = 5000` in `agent_pane.py` for easy tuning.

2. **`ctrl+c` handling at app level vs OS signal**
   - What we know: Textual's `priority=True` binding on `ctrl+c` intercepts before Textual's built-in quit
   - What's unclear: On some terminals, Ctrl-C sends SIGINT before Textual's key handler can process it
   - Recommendation: Implement both: the `BINDINGS` approach for the confirmation dialog, and a `signal.signal(SIGINT, ...)` handler in `main()` as a backup. Test in Phase 2; if SIGINT fires before Textual, consider `Binding("ctrl+c", ...)` with `priority=True` plus `App.exit()` as a fallback in the signal handler.

3. **Divider character rendering**
   - What we know: A `Static("│", id="divider")` with `width: 1` renders a single character column
   - What's unclear: Whether the box-drawing character `│` (U+2502) renders correctly on all target terminals without font issues
   - Recommendation: Use `│` (U+2502) as the default. Test on macOS Terminal.app and iTerm2. Fall back to `|` (ASCII pipe) if rendering issues appear.

---

## Sources

### Primary (HIGH confidence)
- https://textual.textualize.io/guide/layout/ — Horizontal container, fr units, layout patterns
- https://textual.textualize.io/guide/input/ — BINDINGS, key handling, focus
- https://textual.textualize.io/guide/screens/ — ModalScreen, push_screen, dismiss pattern
- https://textual.textualize.io/guide/testing/ — Pilot, run_test(), key press simulation
- https://textual.textualize.io/widgets/rich_log/ — RichLog API, max_lines, write() signature
- https://github.com/Textualize/textual/blob/main/docs/examples/widgets/rich_log.py — Official RichLog + Syntax example
- https://github.com/Textualize/textual/blob/main/src/textual/widgets/_rich_log.py — max_lines implementation source
- https://github.com/Textualize/textual/blob/main/pyproject.toml — Textual 8.0.0 dependencies (rich >=14.2.0, pygments ^2.19.2)
- https://pypi.org/project/textual/ — Confirmed Textual 8.0.0 is current stable, released 2026-02-16
- https://rich.readthedocs.io/en/stable/introduction.html — Rich 14.1.0; Syntax class backed by pygments

### Secondary (MEDIUM confidence)
- https://textual.textualize.io/blog/2025/05/07/the-future-of-textualize/ — Textualize company shutdown; Textual continues as open-source
- https://textual.textualize.io/api/containers/ — VerticalScroll, ScrollableContainer hierarchy confirmed
- GitHub issue #5474 — Ctrl-C + ModalScreen interaction bug; relevant for Phase 4, lower concern in Phase 2

### Tertiary (LOW confidence)
- General web results re: `on_resize` and responsive layout — confirmed by official docs that `fr` units handle resize automatically without event handlers needed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Textual 8.0.0 confirmed on PyPI; Rich version confirmed from Textual's own pyproject.toml
- Architecture patterns: HIGH — all patterns sourced from official Textual docs and verified example code
- Version constraint: HIGH (concern flagged) — roadmap pin `<1.0` is incorrect for current Textual 8.0.0; must update
- Pitfalls: HIGH — Phase 1 sys.path pitfall from STATE.md; Textual binding pitfalls from official docs and GitHub issues
- Syntax highlighting approach: HIGH — official RichLog example uses `Syntax` objects directly; this is the documented pattern

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (Textual releases frequently; re-check version and CHANGELOG before implementing if more than 30 days pass)
