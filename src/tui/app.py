"""AgentBureauApp — the main Textual application for Agent Bureau.

Layout (top to bottom):
  1. StatusBar (id="status-bar") — docked top, always visible, keyboard hints
  2. Horizontal container with AgentPane x2 + divider — fills remaining height
  3. ReconciliationPanel (id="recon-panel") — hidden by default, appears after reconciliation
  4. PromptBar (id="prompt-bar") containing Input(id="prompt-input") — docked bottom

Keyboard bindings:
  left / right  — switch pane focus
  up / down     — scroll focused pane (handled by AgentPane, NOT here)
  q             — exit immediately
  ctrl+c        — push QuitScreen confirmation dialog
  ctrl+l        — clear both panes and reset status bar
  escape        — end debate (only active during DEBATING state)
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
from tui.messages import (
    AgentFinished, ClassificationDone, TokenReceived,
    RoundBoundary, DebateEnded, ReconciliationReady, ApplyResult,
)
from tui.session import SessionState
from tui.widgets.agent_pane import AgentPane
from tui.widgets.prompt_bar import PromptBar
from tui.widgets.quit_screen import QuitScreen
from tui.widgets.status_bar import StatusBar
from tui.widgets.flow_picker_screen import FlowPickerScreen
from tui.widgets.winner_picker_screen import WinnerPickerScreen
from tui.widgets.end_debate_screen import ConfirmEndDebateScreen
from tui.widgets.apply_confirm_screen import ApplyConfirmScreen
from tui.widgets.reconciliation_panel import ReconciliationPanel
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
        Binding("escape", "end_debate", "End debate", show=False),
    ]

    # Session state machine — drives Input.disabled and status bar content.
    session_state: reactive[SessionState] = reactive(SessionState.IDLE)

    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal():
            yield AgentPane(agent_name="claude", id="pane-left")
            yield Static("│", id="divider")
            yield AgentPane(agent_name="codex", id="pane-right")
        yield ReconciliationPanel(id="recon-panel")  # hidden by default
        yield PromptBar(id="prompt-bar")

    def on_mount(self) -> None:
        # Focus the left pane so arrow keys work immediately on startup.
        self.query_one("#pane-left", AgentPane).focus()
        # Initialize tracking state.
        self._terminal_events: dict[str, BridgeEvent] = {}
        self._agent_line_counts: dict[str, int] = {"claude": 0, "codex": 0}
        # Phase 4 state
        self._debate_stop: asyncio.Event = asyncio.Event()
        self._last_texts: dict[str, str] = {}   # {agent_name: full accumulated text}
        self._agreed_code: str = ""
        self._agreed_language: str = "python"
        self._agreed_filename: str | None = None

    def watch_session_state(self, state: SessionState) -> None:
        """Toggle prompt input disabled state based on session state."""
        try:
            prompt_input = self.query_one("#prompt-input", Input)
            prompt_input.disabled = state != SessionState.IDLE
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
        self._last_texts = {}
        self._agreed_code = ""
        self._agreed_language = "python"
        self._agreed_filename = None
        self._debate_stop.clear()

        # Hide reconciliation panel from previous session.
        recon = self.query_one("#recon-panel", ReconciliationPanel)
        recon.hide_panel()

        # Write a visual run separator to both panes.
        separator = "\u2500" * 60
        self.query_one("#pane-left", AgentPane).write_token(separator)
        self.query_one("#pane-right", AgentPane).write_token(separator)

        self.session_state = SessionState.FLOW_PICK
        self.run_worker(
            self._run_session(prompt),
            exclusive=True,
            exit_on_error=False,
            name="bridge-session",
        )

    async def _run_session(self, prompt: str) -> None:
        """Worker: show flow picker, then route to pick-one or live-debate."""
        flow: str = await self.push_screen(
            FlowPickerScreen(), wait_for_dismiss=True
        )
        if flow == "live-debate":
            await self._run_live_debate(prompt)
        else:
            await self._run_pick_one(prompt)

    async def _run_pick_one(self, prompt: str) -> None:
        """Worker: fan-out to both agents, collect responses, then go to pick-winner."""
        from tui.bridge import _stream_pipe, CLAUDE, CODEX

        self.session_state = SessionState.STREAMING
        q: asyncio.Queue[BridgeEvent] = asyncio.Queue()
        stream_fn = _stream_pipe

        task_a = asyncio.create_task(stream_fn(CLAUDE, prompt, 60.0, q))
        task_b = asyncio.create_task(stream_fn(CODEX, prompt, 60.0, q))

        collected: dict[str, list[str]] = {"claude": [], "codex": []}
        terminal_count = 0
        while terminal_count < 2:
            event = await q.get()
            if event.type == "token":
                self.post_message(TokenReceived(agent=event.agent, text=event.text))
                collected[event.agent].append(event.text)
            elif event.type in ("done", "error", "timeout"):
                self.post_message(AgentFinished(agent=event.agent, event=event))
                terminal_count += 1

        await asyncio.gather(task_a, task_b)
        self._last_texts = {k: "\n".join(v) for k, v in collected.items()}
        self.post_message(DebateEnded())

    async def _run_live_debate(self, prompt: str) -> None:
        """Worker: run up to MAX_ROUNDS of debate with round-boundary markers."""
        from tui.bridge import _stream_pipe, CLAUDE, CODEX

        MAX_ROUNDS = 3  # Claude's discretion default; change this constant to adjust
        self._debate_stop.clear()
        self.session_state = SessionState.DEBATING
        stream_fn = _stream_pipe

        last_claude = ""
        last_codex = ""

        for round_num in range(1, MAX_ROUNDS + 1):
            if self._debate_stop.is_set():
                break

            self.post_message(RoundBoundary(round_num=round_num))
            self.query_one("#status-bar", StatusBar).show_debating(round_num, MAX_ROUNDS)

            if round_num == 1:
                claude_prompt = prompt
                codex_prompt = prompt
            else:
                claude_prompt = (
                    f"Original task: {prompt}\n\n"
                    f"The other agent proposed:\n{last_codex}\n\n"
                    f"Refine your approach, incorporating the strengths of theirs. Be concise."
                )
                codex_prompt = (
                    f"Original task: {prompt}\n\n"
                    f"The other agent proposed:\n{last_claude}\n\n"
                    f"Refine your approach, incorporating the strengths of theirs. Be concise."
                )

            q: asyncio.Queue[BridgeEvent] = asyncio.Queue()
            task_a = asyncio.create_task(stream_fn(CLAUDE, claude_prompt, 60.0, q))
            task_b = asyncio.create_task(stream_fn(CODEX, codex_prompt, 60.0, q))

            collected: dict[str, list[str]] = {"claude": [], "codex": []}
            terminal_count = 0
            while terminal_count < 2:
                event = await q.get()
                if event.type == "token":
                    self.post_message(TokenReceived(agent=event.agent, text=event.text))
                    collected[event.agent].append(event.text)
                elif event.type in ("done", "error", "timeout"):
                    self.post_message(AgentFinished(agent=event.agent, event=event))
                    terminal_count += 1

            await asyncio.gather(task_a, task_b)
            last_claude = "\n".join(collected["claude"])
            last_codex = "\n".join(collected["codex"])

        self._last_texts = {"claude": last_claude, "codex": last_codex}
        self.post_message(DebateEnded())

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

    def on_round_boundary(self, message: RoundBoundary) -> None:
        """Insert a round divider into both agent panes."""
        divider = f"\u2500\u2500 Round {message.round_num} \u2500\u2500"
        self.query_one("#pane-left", AgentPane).write_token(divider)
        self.query_one("#pane-right", AgentPane).write_token(divider)

    def on_debate_ended(self, message: DebateEnded) -> None:
        """Debate or pick-one streaming complete — push winner picker."""
        self.session_state = SessionState.PICK_WINNER
        self.query_one("#status-bar", StatusBar).show_pick_winner()
        self.run_worker(
            self._pick_winner_flow(),
            exclusive=False,
            exit_on_error=False,
            name="pick-winner",
        )

    async def _pick_winner_flow(self) -> None:
        """Worker: show WinnerPickerScreen, then route to reconciliation or cancel."""
        winner: str = await self.push_screen(
            WinnerPickerScreen(), wait_for_dismiss=True
        )
        if winner == "cancel":
            self.post_message(ApplyResult(confirmed=False, files_written=[]))
            return
        if winner == "keep-discussing":
            # Re-push the picker to let user reconsider.
            winner2: str = await self.push_screen(
                WinnerPickerScreen(), wait_for_dismiss=True
            )
            if winner2 in ("cancel", "keep-discussing"):
                self.post_message(ApplyResult(confirmed=False, files_written=[]))
                return
            winner = winner2

        winning_agent = "claude" if winner == "agent-a" else "codex"
        losing_agent = "codex" if winner == "agent-a" else "claude"
        await self._run_reconciliation(winning_agent, losing_agent)

    async def _run_reconciliation(self, winner: str, other: str) -> None:
        """Worker: feed both proposals to winner agent for reconciliation, then show diff."""
        from tui.bridge import _stream_pipe, CLAUDE
        from tui.apply import extract_code_proposals, generate_unified_diff

        self.session_state = SessionState.RECONCILING
        self.query_one("#status-bar", StatusBar).show_reconciling()

        winner_text = self._last_texts.get(winner, "")
        other_text = self._last_texts.get(other, "")

        # Collaborative reconciliation prompt (not adversarial — per CONTEXT.md)
        recon_prompt = (
            f"Here is what Agent A proposed:\n{winner_text}\n\n"
            f"Here is what Agent B proposed:\n{other_text}\n\n"
            f"These are complementary perspectives. Produce the best unified solution "
            f"that incorporates the strengths of both. "
            f"First write a brief plain-language explanation of how you merged the two approaches. "
            f"Then provide the final code in a fenced code block, with the target filename "
            f"as the first line (e.g. # src/module.py)."
        )

        q: asyncio.Queue[BridgeEvent] = asyncio.Queue()
        stream_fn = _stream_pipe
        task = asyncio.create_task(stream_fn(CLAUDE, recon_prompt, 90.0, q))

        recon_tokens: list[str] = []
        while True:
            event = await q.get()
            if event.type == "token":
                recon_tokens.append(event.text)
            elif event.type in ("done", "error", "timeout"):
                break
        await task

        full_recon = "\n".join(recon_tokens)

        # Extract agreed code proposal
        proposals = extract_code_proposals(full_recon)
        if proposals:
            agreed = proposals[-1]  # Use the last code block (final proposal)
            self._agreed_code = agreed.code
            self._agreed_language = agreed.language
            self._agreed_filename = agreed.filename
        else:
            self._agreed_code = ""
            self._agreed_language = "text"
            self._agreed_filename = None

        # Generate diff between winner's original and agreed code
        winner_proposals = extract_code_proposals(winner_text)
        original_code = winner_proposals[-1].code if winner_proposals else ""
        diff_text = generate_unified_diff(
            original_code, self._agreed_code,
            fromfile=winner, tofile="reconciled"
        )

        self.post_message(ReconciliationReady(
            discussion_text=full_recon,
            diff_text=diff_text,
            agreed_code=self._agreed_code,
            language=self._agreed_language,
        ))

    def on_reconciliation_ready(self, message: ReconciliationReady) -> None:
        """Show reconciliation panel, then push apply confirm screen."""
        recon_panel = self.query_one("#recon-panel", ReconciliationPanel)
        recon_panel.show_reconciliation(message.discussion_text, message.diff_text)

        file_count = 1 if self._agreed_filename else 0
        self.session_state = SessionState.CONFIRMING_APPLY
        self.query_one("#status-bar", StatusBar).show_apply_confirm(file_count)

        self.run_worker(
            self._apply_confirm_flow(message),
            exclusive=False,
            exit_on_error=False,
            name="apply-confirm",
        )

    async def _apply_confirm_flow(self, recon: ReconciliationReady) -> None:
        """Worker: push ApplyConfirmScreen, write files only if user confirms."""
        from tui.apply import write_file_atomic

        confirmed: bool = await self.push_screen(
            ApplyConfirmScreen(), wait_for_dismiss=True
        )

        files_written: list[str] = []
        if confirmed and self._agreed_filename and self._agreed_code:
            target = Path(self._agreed_filename)
            write_file_atomic(target, self._agreed_code)
            files_written.append(str(target))

        self.post_message(ApplyResult(confirmed=confirmed, files_written=files_written))

    def on_apply_result(self, message: ApplyResult) -> None:
        """Handle apply result — show outcome and return to IDLE."""
        if message.confirmed and message.files_written:
            status_text = f"Applied — wrote {len(message.files_written)} file(s): {', '.join(message.files_written)}"
        elif message.confirmed:
            status_text = "Applied — no files detected in reconciliation output"
        else:
            status_text = "Cancelled — no files written"

        self.query_one("#status-bar", StatusBar).update(status_text)
        self.session_state = SessionState.IDLE
        self.query_one("#prompt-input", Input).focus()

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

    def action_end_debate(self) -> None:
        """Esc during debate: push confirm screen. Only active in DEBATING state."""
        if self.session_state != SessionState.DEBATING:
            return
        def _on_confirm(confirmed: bool) -> None:
            if confirmed:
                self._debate_stop.set()
        self.push_screen(ConfirmEndDebateScreen(), _on_confirm)


def main() -> None:
    """Entry point for the `agent-bureau` CLI command."""
    AgentBureauApp().run()


if __name__ == "__main__":
    main()
