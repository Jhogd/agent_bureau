"""Tests for ReconciliationPanel widget using Textual's headless Pilot harness."""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import RichLog

from tui.widgets.reconciliation_panel import ReconciliationPanel


class PanelTestApp(App):
    """Minimal host app for testing ReconciliationPanel in isolation."""

    def compose(self) -> ComposeResult:
        yield ReconciliationPanel(id="panel")


@pytest.mark.asyncio
async def test_panel_hidden_by_default():
    """ReconciliationPanel must be hidden (display=False) on mount."""
    # Arrange
    app = PanelTestApp()
    # Act
    async with app.run_test(size=(120, 40)) as pilot:
        panel = app.query_one("#panel", ReconciliationPanel)
        # Assert
        assert panel.display is False


@pytest.mark.asyncio
async def test_show_reconciliation_makes_visible():
    """show_reconciliation() sets display=True on the panel."""
    # Arrange
    app = PanelTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        panel = app.query_one("#panel", ReconciliationPanel)
        assert panel.display is False
        # Act
        panel.show_reconciliation("--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new")
        await pilot.pause()
        # Assert
        assert panel.display is True


@pytest.mark.asyncio
async def test_show_reconciliation_with_diff_writes_content():
    """show_reconciliation() with a diff writes content to the RichLog."""
    # Arrange
    app = PanelTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        panel = app.query_one("#panel", ReconciliationPanel)
        # Act
        panel.show_reconciliation("--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new")
        await pilot.pause()
        log = panel.query_one("#recon-log", RichLog)
        # Assert — the log should have content (lines list populated)
        assert len(log.lines) > 0


@pytest.mark.asyncio
async def test_show_reconciliation_no_diff_shows_placeholder():
    """Empty diff_text causes the 'No code differences detected' message to appear."""
    # Arrange
    app = PanelTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        panel = app.query_one("#panel", ReconciliationPanel)
        # Act — pass empty diff with code found (identical reconciliations)
        panel.show_reconciliation("", code_found=True)
        await pilot.pause()
        log = panel.query_one("#recon-log", RichLog)
        # Assert — log has output (the placeholder message was written)
        assert len(log.lines) > 0
        # The panel should also be visible
        assert panel.display is True


@pytest.mark.asyncio
async def test_show_reconciliation_no_code_shows_failure():
    """code_found=False shows the failure state in the panel."""
    app = PanelTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        panel = app.query_one("#panel", ReconciliationPanel)
        panel.show_reconciliation("", code_found=False)
        await pilot.pause()
        assert panel.display is True
        log = panel.query_one("#recon-log", RichLog)
        assert len(log.lines) > 0


@pytest.mark.asyncio
async def test_hide_panel_hides_widget():
    """hide_panel() makes display=False after show_reconciliation() made it visible."""
    # Arrange
    app = PanelTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        panel = app.query_one("#panel", ReconciliationPanel)
        panel.show_reconciliation("--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new")
        await pilot.pause()
        assert panel.display is True
        # Act
        panel.hide_panel()
        await pilot.pause()
        # Assert
        assert panel.display is False
