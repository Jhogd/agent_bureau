"""ConfirmEndDebateScreen — compact y/n modal to confirm ending a live debate.

Dismiss contract: dismisses with True (end debate) or False (keep going).
"""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label


class ConfirmEndDebateScreen(ModalScreen[bool]):
    """Small centered dialog to confirm ending the live debate early.

    Returns True if user presses 'y' (end debate), False on 'n' or Escape (continue).
    """

    DEFAULT_CSS = """
    ConfirmEndDebateScreen {
        align: center middle;
    }
    #end-dialog {
        width: 50;
        height: 5;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
        content-align: center middle;
    }
    """

    BINDINGS = [
        Binding("y", "confirm", "End debate"),
        Binding("n", "reject", "Keep going"),
        Binding("escape", "reject", "Keep going"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="end-dialog"):
            yield Label("End debate? [y/n]")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_reject(self) -> None:
        self.dismiss(False)
