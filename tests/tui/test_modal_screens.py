"""TDD tests for Phase 4 modal screens.

Tests prove dismiss contracts for:
  - FlowPickerScreen: returns 'pick-one' or 'live-debate'
  - WinnerPickerScreen: returns 'agent-a', 'agent-b', 'keep-discussing', or 'cancel'
  - ConfirmEndDebateScreen: returns True (end) or False (continue)
  - ApplyConfirmScreen: returns True (write) or False (reject)
"""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import OptionList

from tui.widgets.flow_picker_screen import FlowPickerScreen
from tui.widgets.winner_picker_screen import WinnerPickerScreen
from tui.widgets.end_debate_screen import ConfirmEndDebateScreen
from tui.widgets.apply_confirm_screen import ApplyConfirmScreen


# ---------------------------------------------------------------------------
# Minimal wrapper apps — same pattern as tests/tui/test_quit_screen.py
# ---------------------------------------------------------------------------

class FlowPickerTestApp(App):
    """Host app that immediately pushes FlowPickerScreen for testing."""

    def __init__(self):
        super().__init__()
        self.flow_result: str | None = None

    def on_mount(self) -> None:
        self.push_screen(FlowPickerScreen(), self._on_result)

    def _on_result(self, result: str | None) -> None:
        self.flow_result = result


class WinnerPickerTestApp(App):
    """Host app that immediately pushes WinnerPickerScreen for testing."""

    def __init__(self):
        super().__init__()
        self.winner_result: str | None = None

    def on_mount(self) -> None:
        self.push_screen(WinnerPickerScreen(), self._on_result)

    def _on_result(self, result: str | None) -> None:
        self.winner_result = result


class EndDebateTestApp(App):
    """Host app that immediately pushes ConfirmEndDebateScreen for testing."""

    def __init__(self):
        super().__init__()
        self.end_result: bool | None = None

    def on_mount(self) -> None:
        self.push_screen(ConfirmEndDebateScreen(), self._on_result)

    def _on_result(self, result: bool | None) -> None:
        self.end_result = result


class ApplyConfirmTestApp(App):
    """Host app that immediately pushes ApplyConfirmScreen for testing."""

    def __init__(self):
        super().__init__()
        self.apply_result: bool | None = None

    def on_mount(self) -> None:
        self.push_screen(ApplyConfirmScreen(), self._on_result)

    def _on_result(self, result: bool | None) -> None:
        self.apply_result = result


# ---------------------------------------------------------------------------
# FlowPickerScreen tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_flow_picker_has_two_options():
    """FlowPickerScreen OptionList must have exactly 2 options."""
    app = FlowPickerTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        option_list = app.screen.query_one("#flow-options", OptionList)
        assert option_list.option_count == 2


@pytest.mark.asyncio
async def test_flow_picker_default_highlighted():
    """FlowPickerScreen must pre-highlight pick-one (index 0) on mount."""
    app = FlowPickerTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        option_list = app.screen.query_one("#flow-options", OptionList)
        assert option_list.highlighted == 0


@pytest.mark.asyncio
async def test_flow_picker_select_pick_one():
    """Pressing Enter on the default highlighted option dismisses with 'pick-one'."""
    app = FlowPickerTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.flow_result == "pick-one"


@pytest.mark.asyncio
async def test_flow_picker_select_live_debate():
    """Arrow down + Enter dismisses with 'live-debate'."""
    app = FlowPickerTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()
        assert app.flow_result == "live-debate"


# ---------------------------------------------------------------------------
# WinnerPickerScreen tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_winner_picker_has_four_options():
    """WinnerPickerScreen OptionList must have exactly 4 options."""
    app = WinnerPickerTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        option_list = app.screen.query_one("#winner-options", OptionList)
        assert option_list.option_count == 4


# ---------------------------------------------------------------------------
# ConfirmEndDebateScreen tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_confirm_end_debate_y_returns_true():
    """Pressing 'y' in ConfirmEndDebateScreen dismisses with True."""
    app = EndDebateTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        assert app.end_result is True


@pytest.mark.asyncio
async def test_confirm_end_debate_n_returns_false():
    """Pressing 'n' in ConfirmEndDebateScreen dismisses with False."""
    app = EndDebateTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        assert app.end_result is False


# ---------------------------------------------------------------------------
# ApplyConfirmScreen tests
# ---------------------------------------------------------------------------

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
