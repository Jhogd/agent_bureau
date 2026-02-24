"""PromptBar widget — one-line input bar at the bottom of the screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input


class PromptBar(Widget):
    """A one-line prompt input bar at the bottom of the screen.

    Wraps a Textual Input widget with compact=True (no border).
    Disabled while agents are streaming; re-enabled and focused after
    each session completes.

    AgentBureauApp handles Input.Submitted directly — PromptBar is a
    pure layout/containment widget.
    """

    DEFAULT_CSS = """
    PromptBar {
        height: 1;
        background: $surface-darken-1;
        dock: bottom;
    }
    PromptBar Input {
        background: $surface-darken-1;
        border: none;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Enter a prompt and press Enter...",
            id="prompt-input",
            compact=True,
        )
