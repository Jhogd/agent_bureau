"""Integration tests for AgentBureauApp using Textual's headless Pilot harness.

Tests cover:
  - Layout: status bar, two panes, divider, and prompt bar visible at startup
  - Focus: left pane focused on startup; arrow keys switch focus
  - Scrolling: up/down scroll focused pane (does not crash)
  - Exit: q exits; ctrl+c pushes QuitScreen
  - Message routing: TokenReceived routes to correct pane
  - Error display: AgentFinished with error shows error in pane
  - State machine: Input disabled while streaming
  - Classification: disagreement highlight applied when disagreements exist
  - Clear: Ctrl-L clears both panes and resets status bar
  - Reconciliation: ReconciliationReady shows panel and review bar
  - Apply result: confirmed/rejected returns to IDLE
"""
import pytest

from tui.app import AgentBureauApp
from tui.messages import (
    AgentFinished, ClassificationDone, TokenReceived,
    ReconciliationReady, ApplyResult,
)
from tui.session import SessionState
from tui.widgets.agent_pane import AgentPane
from tui.event_bus import AgentDone, AgentError, AgentTimeout


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
async def test_status_bar_present():
    """Status bar should be visible at startup with keyboard hints."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.query_one("#status-bar") is not None


@pytest.mark.asyncio
async def test_prompt_bar_present():
    """Prompt bar should be visible at the bottom on startup."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.query_one("#prompt-bar") is not None
        assert app.query_one("#prompt-input") is not None


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


# --- Message routing tests ---

@pytest.mark.asyncio
async def test_token_received_routes_to_correct_pane():
    """TokenReceived(agent='claude') writes to pane-left; 'codex' to pane-right."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Post a token for claude (left pane)
        app.post_message(TokenReceived(agent="claude", text="hello from claude"))
        await pilot.pause()
        left_pane = app.query_one("#pane-left", AgentPane)
        right_pane = app.query_one("#pane-right", AgentPane)
        assert left_pane.line_count == 1
        assert right_pane.line_count == 0


@pytest.mark.asyncio
async def test_token_received_codex_routes_to_right_pane():
    """TokenReceived(agent='codex') writes to pane-right."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.post_message(TokenReceived(agent="codex", text="hello from codex"))
        await pilot.pause()
        left_pane = app.query_one("#pane-left", AgentPane)
        right_pane = app.query_one("#pane-right", AgentPane)
        assert left_pane.line_count == 0
        assert right_pane.line_count == 1


@pytest.mark.asyncio
async def test_agent_finished_with_error_shows_error_in_pane():
    """AgentFinished with AgentError appends error text to the correct pane."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Post AgentFinished carrying an AgentError for claude
        error_event = AgentError(agent="claude", message="exited with code 1", exit_code=1)
        app.post_message(AgentFinished(agent="claude", event=error_event))
        await pilot.pause()
        left_pane = app.query_one("#pane-left", AgentPane)
        # Error text should have been written to the pane
        assert left_pane.line_count >= 1


# --- State machine tests ---

@pytest.mark.asyncio
async def test_state_machine_disables_input_while_streaming():
    """Setting session_state=STREAMING disables the prompt input."""
    from textual.widgets import Input
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Verify input is enabled initially
        prompt_input = app.query_one("#prompt-input", Input)
        assert not prompt_input.disabled
        # Transition to streaming state
        app.session_state = SessionState.STREAMING
        await pilot.pause()
        assert prompt_input.disabled


@pytest.mark.asyncio
async def test_state_machine_enables_input_when_idle():
    """Returning session_state to IDLE re-enables the prompt input."""
    from textual.widgets import Input
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        prompt_input = app.query_one("#prompt-input", Input)
        # Go to streaming then back to idle
        app.session_state = SessionState.STREAMING
        await pilot.pause()
        assert prompt_input.disabled
        app.session_state = SessionState.IDLE
        await pilot.pause()
        assert not prompt_input.disabled


# --- Classification tests ---

@pytest.mark.asyncio
async def test_classification_done_sets_disagreement_highlight():
    """ClassificationDone with non-empty disagreements adds 'disagreement' class to both panes."""
    from disagree_v1.models import Disagreement
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        disagreements = [Disagreement(kind="approach", summary="Different approaches.")]
        app.post_message(ClassificationDone(disagreements=disagreements, full_texts={}))
        await pilot.pause()
        left_pane = app.query_one("#pane-left", AgentPane)
        right_pane = app.query_one("#pane-right", AgentPane)
        assert "disagreement" in left_pane.classes
        assert "disagreement" in right_pane.classes


@pytest.mark.asyncio
async def test_classification_done_without_disagreements_no_highlight():
    """ClassificationDone with empty disagreements does not add 'disagreement' class."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.post_message(ClassificationDone(disagreements=[], full_texts={}))
        await pilot.pause()
        left_pane = app.query_one("#pane-left", AgentPane)
        right_pane = app.query_one("#pane-right", AgentPane)
        assert "disagreement" not in left_pane.classes
        assert "disagreement" not in right_pane.classes


# --- Clear tests ---

@pytest.mark.asyncio
async def test_ctrl_l_clears_both_panes():
    """Ctrl-L clears both panes simultaneously."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Write tokens to both panes
        app.post_message(TokenReceived(agent="claude", text="token 1"))
        app.post_message(TokenReceived(agent="codex", text="token 2"))
        await pilot.pause()
        left_pane = app.query_one("#pane-left", AgentPane)
        right_pane = app.query_one("#pane-right", AgentPane)
        assert left_pane.line_count >= 1
        assert right_pane.line_count >= 1
        # Press ctrl+l to clear
        await pilot.press("ctrl+l")
        await pilot.pause()
        assert left_pane.line_count == 0
        assert right_pane.line_count == 0


# --- Reconciliation tests ---

@pytest.mark.asyncio
async def test_reconciliation_ready_shows_panel():
    """Post ReconciliationReady and verify ReconciliationPanel becomes visible."""
    from tui.widgets.reconciliation_panel import ReconciliationPanel
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Panel should be hidden initially
        recon_panel = app.query_one("#recon-panel", ReconciliationPanel)
        assert not recon_panel.display
        # Post reconciliation ready message
        app.post_message(ReconciliationReady(
            discussion_text="discuss",
            diff_text="",
            agreed_code="",
            language="python",
        ))
        await pilot.pause()
        # Panel should now be visible
        assert recon_panel.display


@pytest.mark.asyncio
async def test_reconciliation_ready_shows_review_bar():
    """Post ReconciliationReady and verify ReviewBar becomes visible."""
    from tui.widgets.review_bar import ReviewBar
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        review_bar = app.query_one("#review-bar", ReviewBar)
        assert not review_bar.display
        app.post_message(ReconciliationReady(
            discussion_text="discuss",
            diff_text="",
            agreed_code="",
            language="python",
        ))
        await pilot.pause()
        assert review_bar.display


@pytest.mark.asyncio
async def test_reconciliation_ready_sets_reviewing_state():
    """Post ReconciliationReady and verify session_state transitions to REVIEWING."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.post_message(ReconciliationReady(
            discussion_text="discuss",
            diff_text="",
            agreed_code="",
            language="python",
        ))
        await pilot.pause()
        assert app.session_state == SessionState.REVIEWING


# --- Apply result tests ---

@pytest.mark.asyncio
async def test_apply_result_confirmed_returns_to_idle():
    """Post ApplyResult(confirmed=True) and verify session returns to IDLE."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # Simulate being in CONFIRMING_APPLY state
        app.session_state = SessionState.CONFIRMING_APPLY
        await pilot.pause()
        # Post confirmed apply result
        app.post_message(ApplyResult(confirmed=True, files_written=["foo.py"]))
        await pilot.pause()
        assert app.session_state == SessionState.IDLE


@pytest.mark.asyncio
async def test_apply_result_confirmed_shows_applied_in_status():
    """Post ApplyResult(confirmed=True) and verify status bar contains 'Applied'."""
    from tui.widgets.status_bar import StatusBar
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.post_message(ApplyResult(confirmed=True, files_written=["foo.py"]))
        await pilot.pause()
        status_bar = app.query_one("#status-bar", StatusBar)
        assert "Applied" in str(status_bar.render())


@pytest.mark.asyncio
async def test_apply_result_rejected_returns_to_idle():
    """Post ApplyResult(confirmed=False) and verify session returns to IDLE."""
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.session_state = SessionState.CONFIRMING_APPLY
        await pilot.pause()
        app.post_message(ApplyResult(confirmed=False, files_written=[]))
        await pilot.pause()
        assert app.session_state == SessionState.IDLE


@pytest.mark.asyncio
async def test_apply_result_rejected_shows_cancelled_in_status():
    """Post ApplyResult(confirmed=False) and verify status bar contains 'Cancelled'."""
    from tui.widgets.status_bar import StatusBar
    app = AgentBureauApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.post_message(ApplyResult(confirmed=False, files_written=[]))
        await pilot.pause()
        status_bar = app.query_one("#status-bar", StatusBar)
        assert "Cancelled" in str(status_bar.render())
