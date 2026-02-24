"""AgentBureauApp — the main Textual application for Agent Bureau.

Layout (top to bottom):
  1. StatusBar (id="status-bar") — docked top, always visible, keyboard hints
  2. Horizontal container with AgentPane x2 + divider — fills remaining height
  3. PromptBar (id="prompt-bar") containing Input(id="prompt-input") — docked bottom

Keyboard bindings:
  left / right  — switch pane focus
  up / down     — scroll focused pane (handled by AgentPane, NOT here)
  q             — exit immediately
  ctrl+c        — push QuitScreen confirmation dialog
  ctrl+l        — clear both panes and reset status bar
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Input, Static

from tui.event_bus import AgentDone, AgentError, AgentTimeout, BridgeEvent
from tui.messages import AgentFinished, ClassificationDone, TokenReceived
from tui.session import SessionState
from tui.widgets.agent_pane import AgentPane
from tui.widgets.prompt_bar import PromptBar
from tui.widgets.quit_screen import QuitScreen
from tui.widgets.status_bar import StatusBar
from tui.content import SCROLLBACK_LIMIT


class AgentBureauApp(App):
    """Side-by-side columnar TUI for comparing agent responses with live streaming."""

    CSS_PATH = Path(__file__).parent / "styles.tcss"

    BINDINGS = [
        Binding("left", "focus_left", "Left pane", show=False),
        Binding("right", "focus_right", "Right pane", show=False),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "confirm_quit", "Exit", priority=True),
        Binding("ctrl+l", "clear_panes", "Clear", show=False),
    ]

    # Session state machine — drives Input.disabled and status bar content.
    session_state: reactive[SessionState] = reactive(SessionState.IDLE)

    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal():
            yield AgentPane(agent_name="claude", id="pane-left")
            yield Static("│", id="divider")
            yield AgentPane(agent_name="codex", id="pane-right")
        yield PromptBar(id="prompt-bar")

    def on_mount(self) -> None:
        # Focus the left pane so arrow keys work immediately on startup.
        self.query_one("#pane-left", AgentPane).focus()
        # Initialize tracking state.
        self._terminal_events: dict[str, BridgeEvent] = {}
        self._agent_line_counts: dict[str, int] = {"claude": 0, "codex": 0}

    def watch_session_state(self, state: SessionState) -> None:
        """Toggle prompt input disabled state based on session state."""
        try:
            prompt_input = self.query_one("#prompt-input", Input)
            prompt_input.disabled = state in (SessionState.STREAMING, SessionState.CLASSIFYING)
        except Exception:
            # Input may not be mounted yet during early lifecycle.
            pass

    # --- Prompt submission ---

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle prompt submission — gate on IDLE state."""
        prompt = event.value.strip()
        if not prompt or self.session_state != SessionState.IDLE:
            return
        event.input.clear()
        self._start_session(prompt)

    def _start_session(self, prompt: str) -> None:
        """Reset state, write run separator to both panes, launch the bridge worker."""
        self._terminal_events = {}
        self._agent_line_counts = {"claude": 0, "codex": 0}

        # Write a visual run separator to both panes.
        separator = "\u2500" * 60
        self.query_one("#pane-left", AgentPane).write_token(separator)
        self.query_one("#pane-right", AgentPane).write_token(separator)

        self.session_state = SessionState.STREAMING
        self.run_worker(
            self._run_session(prompt),
            exclusive=True,
            exit_on_error=False,
            name="bridge-session",
        )

    async def _run_session(self, prompt: str) -> None:
        """Async worker: fan-out to both agents, post messages for each event."""
        from tui.bridge import _stream_pty, _stream_pipe, _pty_available, CLAUDE, CODEX

        q: asyncio.Queue[BridgeEvent] = asyncio.Queue()
        stream_fn = _stream_pty if _pty_available() else _stream_pipe

        task_a = asyncio.create_task(stream_fn(CLAUDE, prompt, 60.0, q))
        task_b = asyncio.create_task(stream_fn(CODEX, prompt, 60.0, q))

        terminal_count = 0
        while terminal_count < 2:
            event = await q.get()
            if event.type == "token":
                self.post_message(TokenReceived(agent=event.agent, text=event.text))
            elif event.type in ("done", "error", "timeout"):
                self.post_message(AgentFinished(agent=event.agent, event=event))
                terminal_count += 1

        await asyncio.gather(task_a, task_b)

    # --- Message handlers ---

    def on_token_received(self, message: TokenReceived) -> None:
        """Route a streamed token to the correct pane and update status bar."""
        pane_id = "#pane-left" if message.agent == "claude" else "#pane-right"
        pane = self.query_one(pane_id, AgentPane)
        pane.write_token(message.text)
        self._agent_line_counts[message.agent] = (
            self._agent_line_counts.get(message.agent, 0) + 1
        )
        self.query_one("#status-bar", StatusBar).show_streaming(self._agent_line_counts)

        # Safety: clear panes if scrollback limit is reached.
        left = self.query_one("#pane-left", AgentPane)
        right = self.query_one("#pane-right", AgentPane)
        if left.line_count >= SCROLLBACK_LIMIT or right.line_count >= SCROLLBACK_LIMIT:
            self.action_clear_panes()

    def on_agent_finished(self, message: AgentFinished) -> None:
        """Handle a terminal bridge event — store it and trigger classification when both done."""
        event = message.event
        pane_id = "#pane-left" if message.agent == "claude" else "#pane-right"
        pane = self.query_one(pane_id, AgentPane)

        # Append visible error text for non-successful terminal events.
        if isinstance(event, AgentError):
            pane.write_token(f"[error: agent exited with code {event.exit_code}]")
        elif isinstance(event, AgentTimeout):
            pane.write_token("[error: agent timed out]")

        self._terminal_events[message.agent] = event
        self.query_one("#status-bar", StatusBar).show_done(self._agent_line_counts)

        if len(self._terminal_events) == 2:
            self.session_state = SessionState.CLASSIFYING
            self._run_classification()

    def _run_classification(self) -> None:
        """Attempt to classify disagreements between the two agent responses."""
        from disagree_v1.classifier import classify_disagreements
        from disagree_v1.adapters import CommandJsonAdapter
        from disagree_v1.models import AgentResponse

        full_texts: dict[str, str] = {}
        responses: dict[str, AgentResponse] = {}

        # Extract full_text from AgentDone events only.
        for agent_name, event in self._terminal_events.items():
            if isinstance(event, AgentDone):
                full_texts[agent_name] = event.full_text
                # Attempt JSON parsing to build AgentResponse.
                adapter = CommandJsonAdapter(name=agent_name, command_template="")
                try:
                    payload = adapter._parse_payload(event.full_text)
                    response = adapter._validate_payload(payload)
                    responses[agent_name] = response
                except Exception:
                    pass

        disagreements: list = []
        if len(responses) == 2:
            agents = list(responses.values())
            try:
                disagreements = classify_disagreements(agents[0], agents[1])
            except Exception:
                disagreements = []

        self.post_message(ClassificationDone(disagreements=disagreements, full_texts=full_texts))

    def on_classification_done(self, message: ClassificationDone) -> None:
        """Apply classification results to the UI and re-enable input."""
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.show_classification(self._agent_line_counts, message.disagreements)

        has_disagreements = bool(message.disagreements)
        self.query_one("#pane-left", AgentPane).set_disagreement_highlight(has_disagreements)
        self.query_one("#pane-right", AgentPane).set_disagreement_highlight(has_disagreements)

        self.session_state = SessionState.DONE
        # Re-focus prompt input for next submission.
        self.query_one("#prompt-input", Input).focus()
        self.session_state = SessionState.IDLE

    # --- Actions ---

    def action_focus_left(self) -> None:
        self.query_one("#pane-left", AgentPane).focus()

    def action_focus_right(self) -> None:
        self.query_one("#pane-right", AgentPane).focus()

    def action_quit(self) -> None:
        self.exit()

    def action_confirm_quit(self) -> None:
        self.push_screen(QuitScreen(), lambda result: self.exit() if result else None)

    def action_clear_panes(self) -> None:
        """Clear both panes simultaneously and reset status bar to hints."""
        self.query_one("#pane-left", AgentPane).clear()
        self.query_one("#pane-right", AgentPane).clear()
        self._agent_line_counts = {"claude": 0, "codex": 0}
        self.query_one("#status-bar", StatusBar).show_hints()


def main() -> None:
    """Entry point for the `agent-bureau` CLI command."""
    AgentBureauApp().run()


if __name__ == "__main__":
    main()
