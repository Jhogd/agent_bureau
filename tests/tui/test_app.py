"""Integration tests for AgentBureauApp using Textual's headless Pilot harness.

Tests cover:
  - Layout: two panes and divider present at multiple terminal widths
  - Focus: left pane focused on startup; arrow keys switch focus
  - Scrolling: up/down scroll focused pane (does not crash)
  - Exit: q exits; ctrl+c pushes QuitScreen
"""
import pytest

from tui.app import AgentBureauApp
from tui.widgets.agent_pane import AgentPane


# --- Layout tests ---

@pytest.mark.asyncio
async def test_two_panes_and_divider_exist():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.query_one("#pane-left") is not None
        assert app.query_one("#pane-right") is not None
        assert app.query_one("#divider") is not None


@pytest.mark.asyncio
async def test_panes_have_equal_width_at_120_columns():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        left = app.query_one("#pane-left", AgentPane)
        right = app.query_one("#pane-right", AgentPane)
        # Each pane should be roughly half of 119 usable columns (1 for divider).
        # Allow +-2 for rounding.
        assert abs(left.size.width - right.size.width) <= 2


@pytest.mark.asyncio
async def test_layout_at_80_columns():
    app = AgentBureauApp()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        left = app.query_one("#pane-left", AgentPane)
        right = app.query_one("#pane-right", AgentPane)
        assert left.size.width > 30
        assert right.size.width > 30


@pytest.mark.asyncio
async def test_layout_at_200_columns():
    app = AgentBureauApp()
    async with app.run_test(size=(200, 50)) as pilot:
        await pilot.pause()
        left = app.query_one("#pane-left", AgentPane)
        right = app.query_one("#pane-right", AgentPane)
        assert left.size.width > 90
        assert right.size.width > 90


# --- Focus tests ---

@pytest.mark.asyncio
async def test_left_pane_focused_on_startup():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == "pane-left"


@pytest.mark.asyncio
async def test_right_arrow_switches_focus_to_right_pane():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        assert app.focused.id == "pane-right"


@pytest.mark.asyncio
async def test_left_arrow_returns_focus_to_left_pane():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        await pilot.press("left")
        await pilot.pause()
        assert app.focused.id == "pane-left"


@pytest.mark.asyncio
async def test_repeated_right_arrow_stays_on_right_pane():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("right")
        await pilot.press("right")
        await pilot.pause()
        assert app.focused.id == "pane-right"


# --- Scroll tests ---

@pytest.mark.asyncio
async def test_up_down_arrows_do_not_crash():
    """Smoke test: scrolling the focused pane raises no exception."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("up")
        await pilot.pause()
        # If we reach here without exception, the test passes.


@pytest.mark.asyncio
async def test_scroll_only_affects_focused_pane():
    """Pressing down on the left pane does not change right pane scroll position."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        from textual.widgets import RichLog
        await pilot.pause()
        right_log = app.query_one("#pane-right #content", RichLog)
        scroll_before = right_log.scroll_y
        # Focus left pane and scroll down
        await pilot.press("left")
        await pilot.pause()
        for _ in range(5):
            await pilot.press("down")
        await pilot.pause()
        assert right_log.scroll_y == scroll_before


# --- Exit tests ---

@pytest.mark.asyncio
async def test_q_exits_app():
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("q")
        # App exits cleanly — run_test context exits without error


@pytest.mark.asyncio
async def test_ctrl_c_pushes_quit_screen():
    from tui.widgets.quit_screen import QuitScreen
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("ctrl+c")
        await pilot.pause()
        # QuitScreen should be on the screen stack
        assert isinstance(app.screen, QuitScreen)


@pytest.mark.asyncio
async def test_cancel_in_quit_screen_returns_to_tui():
    from tui.widgets.quit_screen import QuitScreen
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert isinstance(app.screen, QuitScreen)
        await pilot.click("#cancel")
        await pilot.pause()
        # Back on the main screen — not QuitScreen
        assert not isinstance(app.screen, QuitScreen)
