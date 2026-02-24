"""ApplyConfirmScreen — y/n confirmation gate before writing files to disk.

Dismiss contract: dismisses with True (write files) or False (reject/cancel).
No file is written without an explicit 'y' from this screen.
"""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label


class ApplyConfirmScreen(ModalScreen[bool]):
    """Centered confirmation dialog before applying proposed code changes.

    Returns True if user presses 'y' (write files), False on 'n' or Escape (cancel).
    """

    DEFAULT_CSS = """
    ApplyConfirmScreen {
        align: center middle;
    }
    #apply-dialog {
        width: 60;
        height: 7;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
        content-align: center middle;
    }
    """

    BINDINGS = [
        Binding("y", "confirm", "Write files"),
        Binding("n", "reject", "Cancel"),
        Binding("escape", "reject", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="apply-dialog"):
            yield Label("Apply changes? Press y to write files, n to cancel.")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_reject(self) -> None:
        self.dismiss(False)
