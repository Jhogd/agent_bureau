"""AgentPane widget — a labeled, independently scrollable pane for agent output."""
from rich.ansi import AnsiDecoder
from rich.text import Text
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
    _ansi_decoder = AnsiDecoder()

    BINDINGS = [
        Binding("up", "scroll_up", "Scroll up", show=False),
        Binding("down", "scroll_down", "Scroll down", show=False),
        Binding("pageup", "scroll_page_up", "Page up", show=False),
        Binding("pagedown", "scroll_page_down", "Page down", show=False),
    ]

    def __init__(self, agent_name: str, **kwargs) -> None:
        self.agent_name = agent_name
        self._has_content = False
        self._line_count: int = 0
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

    @property
    def line_count(self) -> int:
        """Number of lines written via write_token()."""
        return self._line_count

    def write_token(self, line: str) -> None:
        """Write a single streamed token line to the RichLog.

        Decodes ANSI escape sequences before writing so Rich does not
        interpret them as markup. Increments the internal line counter.
        """
        log = self.query_one("#content", RichLog)
        if not self._has_content:
            self._has_content = True
            self.query_one("#placeholder", Label).display = False
            log.display = True
        # Use next() with a fallback so an empty line doesn't crash.
        rich_text = next(self._ansi_decoder.decode(line), Text(line))
        log.write(rich_text)
        self._line_count += 1

    def clear(self) -> None:
        """Reset the pane to its empty state (placeholder visible, RichLog cleared)."""
        log = self.query_one("#content", RichLog)
        log.clear()
        log.display = False
        self.query_one("#placeholder", Label).display = True
        self._has_content = False
        self._line_count = 0

    def set_disagreement_highlight(self, active: bool) -> None:
        """Add or remove the 'disagreement' CSS class on this pane.

        When active=True, the pane header changes color (per styles.tcss).
        """
        if active:
            self.add_class("disagreement")
        else:
            self.remove_class("disagreement")

    def action_scroll_up(self) -> None:
        self.query_one("#content", RichLog).scroll_up(animate=False)

    def action_scroll_down(self) -> None:
        self.query_one("#content", RichLog).scroll_down(animate=False)

    def action_scroll_page_up(self) -> None:
        self.query_one("#content", RichLog).scroll_page_up(animate=False)

    def action_scroll_page_down(self) -> None:
        self.query_one("#content", RichLog).scroll_page_down(animate=False)
