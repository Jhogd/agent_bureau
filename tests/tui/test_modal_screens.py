"""TDD tests for modal screens.

Tests prove dismiss contracts for:
  - ApplyConfirmScreen: returns True (write) or False (reject)
"""
import pytest
from textual.app import App, ComposeResult

from tui.widgets.apply_confirm_screen import ApplyConfirmScreen


class ApplyConfirmTestApp(App):
    """Host app that immediately pushes ApplyConfirmScreen for testing."""

    def __init__(self):
        super().__init__()
        self.apply_result: bool | None = None

    def on_mount(self) -> None:
        self.push_screen(ApplyConfirmScreen(), self._on_result)

    def _on_result(self, result: bool | None) -> None:
        self.apply_result = result


@pytest.mark.asyncio
async def test_apply_confirm_y_returns_true():
    """Pressing 'y' in ApplyConfirmScreen dismisses with True."""
    app = ApplyConfirmTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        assert app.apply_result is True


@pytest.mark.asyncio
async def test_apply_confirm_n_returns_false():
    """Pressing 'n' in ApplyConfirmScreen dismisses with False."""
    app = ApplyConfirmTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        assert app.apply_result is False


@pytest.mark.asyncio
async def test_apply_confirm_escape_returns_false():
    """Pressing 'escape' in ApplyConfirmScreen dismisses with False."""
    app = ApplyConfirmTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.apply_result is False
