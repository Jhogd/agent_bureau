"""Tests for AgentPane widget using Textual's headless Pilot harness."""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label, RichLog

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


# NEW TESTS — streaming extensions


@pytest.mark.asyncio
async def test_write_token_appends_to_richlog():
    """write_token() writes a single line to the RichLog and reveals it."""
    app = PaneTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one("#pane", AgentPane)
        pane.write_token("hello world")
        log = pane.query_one("#content", RichLog)
        assert log.display is True


@pytest.mark.asyncio
async def test_write_token_increments_line_count():
    """line_count tracks the number of write_token() calls."""
    app = PaneTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one("#pane", AgentPane)
        assert pane.line_count == 0
        pane.write_token("line 1")
        assert pane.line_count == 1
        pane.write_token("line 2")
        assert pane.line_count == 2


@pytest.mark.asyncio
async def test_write_token_decodes_ansi():
    """write_token() accepts ANSI escape sequences without raising."""
    app = PaneTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one("#pane", AgentPane)
        # Should not raise; AnsiDecoder handles the escape sequence
        pane.write_token("\x1b[32mgreen text\x1b[0m")
        assert pane.line_count == 1


@pytest.mark.asyncio
async def test_clear_resets_pane():
    """clear() resets line_count, hides RichLog, shows placeholder."""
    app = PaneTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one("#pane", AgentPane)
        pane.write_token("some content")
        assert pane.line_count == 1
        pane.clear()
        assert pane.line_count == 0
        log = pane.query_one("#content", RichLog)
        placeholder = pane.query_one("#placeholder", Label)
        assert log.display is False
        assert placeholder.display is True


@pytest.mark.asyncio
async def test_disagreement_highlight_added_and_removed():
    """set_disagreement_highlight(True/False) adds/removes CSS class."""
    app = PaneTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one("#pane", AgentPane)
        pane.set_disagreement_highlight(True)
        assert pane.has_class("disagreement")
        pane.set_disagreement_highlight(False)
        assert not pane.has_class("disagreement")
