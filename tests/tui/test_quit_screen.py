"""Tests for QuitScreen modal widget."""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button

from tui.widgets.quit_screen import QuitScreen


class QuitTestApp(App):
    """Host app that immediately pushes the QuitScreen for testing."""

    def __init__(self):
        super().__init__()
        self.quit_result: bool | None = None

    def on_mount(self) -> None:
        self.push_screen(QuitScreen(), self._on_result)

    def _on_result(self, result: bool | None) -> None:
        self.quit_result = result


@pytest.mark.asyncio
async def test_quit_button_dismisses_with_true():
    app = QuitTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.click("#quit")
        await pilot.pause()
        assert app.quit_result is True


@pytest.mark.asyncio
async def test_cancel_button_dismisses_with_false():
    app = QuitTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.click("#cancel")
        await pilot.pause()
        assert app.quit_result is False


@pytest.mark.asyncio
async def test_dialog_contains_quit_and_cancel_buttons():
    app = QuitTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Query from the active screen (the modal) rather than the app root
        quit_btn = app.screen.query_one("#quit", Button)
        cancel_btn = app.screen.query_one("#cancel", Button)
        assert quit_btn is not None
        assert cancel_btn is not None
