"""FlowPickerScreen — slim top-banner modal for choosing session flow.

Dismiss contract: dismisses with 'pick-one' or 'live-debate' (str).
Ctrl-C quits the app (priority binding); pick-one is pre-highlighted as default.
"""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets._option_list import Option


class FlowPickerScreen(ModalScreen[str]):
    """Top-banner flow selection modal.

    Returns 'pick-one' or 'live-debate' on dismiss.
    Ctrl-C quits the app from this screen (standard exit before forced choice).
    """

    DEFAULT_CSS = """
    FlowPickerScreen {
        align: left top;
        background: transparent;
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

    BINDINGS = [
        Binding("ctrl+c", "app.quit", "Quit", priority=True),
    ]

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
        ol.highlighted = 0  # pre-highlight pick-one as the default path

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option_id)
