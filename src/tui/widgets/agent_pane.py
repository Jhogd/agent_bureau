"""AgentPane widget — a labeled, independently scrollable pane for agent output."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Label, RichLog

from tui.content import write_content_to_pane, SCROLLBACK_LIMIT


class AgentPane(Widget):
    """A focusable widget that displays a labeled, scrollable agent output pane.

    Composes:
      - A docked header Label showing the agent name (brighter when focused, dimmed when not)
      - A placeholder Label shown when the pane has no content yet
      - A RichLog for streamed/written content (hidden until first write)

    Keyboard bindings (active when this pane has focus):
      - up / down: scroll the RichLog line by line
      - page_up / page_down: scroll the RichLog one screen at a time (bonus shortcut)
    """

    can_focus = True

    BINDINGS = [
        Binding("up", "scroll_up", "Scroll up", show=False),
        Binding("down", "scroll_down", "Scroll down", show=False),
        Binding("pageup", "scroll_page_up", "Page up", show=False),
        Binding("pagedown", "scroll_page_down", "Page down", show=False),
    ]

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
            markup=True,
            max_lines=SCROLLBACK_LIMIT,
            auto_scroll=True,
        )

    def on_mount(self) -> None:
        # Hide the RichLog until the first write; show placeholder instead.
        self.query_one("#content", RichLog).display = False

    def write_content(self, text: str) -> None:
        """Write agent output text to the pane, showing the RichLog on first call."""
        log = self.query_one("#content", RichLog)
        if not self._has_content:
            self._has_content = True
            self.query_one("#placeholder", Label).display = False
            log.display = True
        write_content_to_pane(log, text)

    def action_scroll_up(self) -> None:
        self.query_one("#content", RichLog).scroll_up(animate=False)

    def action_scroll_down(self) -> None:
        self.query_one("#content", RichLog).scroll_down(animate=False)

    def action_scroll_page_up(self) -> None:
        self.query_one("#content", RichLog).scroll_page_up(animate=False)

    def action_scroll_page_down(self) -> None:
        self.query_one("#content", RichLog).scroll_page_down(animate=False)
