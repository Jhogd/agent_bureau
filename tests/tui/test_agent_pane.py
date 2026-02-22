"""Tests for AgentPane widget using Textual's headless Pilot harness."""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import RichLog

from tui.widgets.agent_pane import AgentPane


class PaneTestApp(App):
    """Minimal host app for testing AgentPane in isolation."""

    def compose(self) -> ComposeResult:
        yield AgentPane(agent_name="claude", id="pane")

    def on_mount(self) -> None:
        self.query_one("#pane").focus()


@pytest.mark.asyncio
async def test_agent_name_appears_in_header():
    app = PaneTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        header = app.query_one("#pane #header")
        assert "claude" in str(header.render())


@pytest.mark.asyncio
async def test_placeholder_visible_before_any_write():
    app = PaneTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        placeholder = app.query_one("#pane #placeholder")
        assert placeholder.display is True
        log = app.query_one("#pane #content", RichLog)
        assert log.display is False


@pytest.mark.asyncio
async def test_write_content_hides_placeholder_shows_log():
    app = PaneTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        pane = app.query_one("#pane", AgentPane)
        pane.write_content("Hello from claude")
        await pilot.pause()
        placeholder = app.query_one("#pane #placeholder")
        log = app.query_one("#pane #content", RichLog)
        assert placeholder.display is False
        assert log.display is True


@pytest.mark.asyncio
async def test_richlog_has_bounded_scrollback():
    app = PaneTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        log = app.query_one("#pane #content", RichLog)
        assert log.max_lines == 5000


@pytest.mark.asyncio
async def test_pane_is_focusable():
    app = PaneTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        pane = app.query_one("#pane", AgentPane)
        assert pane.can_focus is True
