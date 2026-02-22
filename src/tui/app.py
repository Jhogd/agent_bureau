"""AgentBureauApp — the main Textual application for Agent Bureau.

Layout: two AgentPane columns separated by a single-character vertical divider,
filling the full terminal height. Left pane focuses on startup.

Keyboard bindings:
  left / right  — switch pane focus
  up / down     — scroll focused pane (handled by AgentPane, NOT here)
  q             — exit immediately
  ctrl+c        — push QuitScreen confirmation dialog
"""
from pathlib import Path
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static

from tui.widgets.agent_pane import AgentPane
from tui.widgets.quit_screen import QuitScreen

# Placeholder content for Phase 2 validation — replaced by live streaming in Phase 3
_PLACEHOLDER_CONTENT = """\
This is example agent output for layout validation.

Here is some prose describing an approach to the problem.
The agent would normally stream this content token by token.

```python
def solve(n: int) -> int:
    \"\"\"Example code block for syntax highlight validation.\"\"\"
    if n <= 1:
        return n
    return solve(n - 1) + solve(n - 2)
```

After the code block, prose continues here.
Use `left` and `right` arrow keys to switch panes.
Use `up` and `down` arrow keys to scroll this pane.
Press `q` to quit, or `Ctrl-C` for a confirmation dialog.
"""


class AgentBureauApp(App):
    """Side-by-side columnar TUI for comparing agent responses."""

    CSS_PATH = Path(__file__).parent / "styles.tcss"

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
        # Explicitly focus the left pane so arrow keys work immediately on startup.
        # Without this call, no pane is focused and key bindings are silent.
        self.query_one("#pane-left", AgentPane).focus()
        # Load placeholder content into both panes for Phase 2 layout validation.
        self.query_one("#pane-left", AgentPane).write_content(_PLACEHOLDER_CONTENT)
        self.query_one("#pane-right", AgentPane).write_content(_PLACEHOLDER_CONTENT)

    def action_focus_left(self) -> None:
        self.query_one("#pane-left", AgentPane).focus()

    def action_focus_right(self) -> None:
        self.query_one("#pane-right", AgentPane).focus()

    def action_quit(self) -> None:
        self.exit()

    def action_confirm_quit(self) -> None:
        self.push_screen(QuitScreen(), lambda result: self.exit() if result else None)


def main() -> None:
    """Entry point for the `agent-bureau` CLI command."""
    AgentBureauApp().run()


if __name__ == "__main__":
    main()
