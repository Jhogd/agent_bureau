"""WinnerPickerScreen — overlay modal for picking the debate winner.

Dismiss contract: dismisses with one of 'agent-a', 'agent-b',
'keep-discussing', or 'cancel' (str).
Escape dismisses with 'cancel'.
"""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets._option_list import Option


class WinnerPickerScreen(ModalScreen[str]):
    """Overlay modal for picking a debate winner.

    Returns one of 'agent-a', 'agent-b', 'keep-discussing', or 'cancel' on dismiss.
    Escape cancels (no changes).
    """

    DEFAULT_CSS = """
    WinnerPickerScreen {
        align: center middle;
        background: transparent;
    }
    #winner-banner {
        width: 50;
        height: auto;
        background: $panel-darken-2;
        border: thick $background 80%;
        padding: 0 1;
    }
    #winner-options {
        width: 100%;
        height: auto;
        border: none;
        padding: 0;
    }
    """

    BINDINGS = [
        Binding("escape", "action_cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="winner-banner"):
            yield Label("Pick a winner:")
            yield OptionList(
                Option("Agent A wins", id="agent-a"),
                Option("Agent B wins", id="agent-b"),
                Option("Keep discussing", id="keep-discussing"),
                Option("Cancel (no changes)", id="cancel"),
                id="winner-options",
                compact=True,
            )

    def on_mount(self) -> None:
        self.query_one("#winner-options", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option_id)

    def action_cancel(self) -> None:
        self.dismiss("cancel")
