"""AgentBureauApp — the main Textual application for Agent Bureau.

Layout (top to bottom):
  1. StatusBar (id="status-bar") — docked top
  2. Horizontal container with AgentPane x2 + divider — fills remaining height
  3. ReconciliationPanel (id="recon-panel") — hidden until reconciliation completes
  4. ReviewBar (id="review-bar") — hidden until reconciliation completes
  5. PromptBar (id="prompt-bar") — docked bottom

Flow:
  User submits prompt → both agents stream simultaneously → classification →
  auto-reconciliation → ReviewBar appears with options:
    [r] Reconcile again  [c] Accept Claude  [x] Accept Codex  [y] Apply reconciled

Keyboard bindings:
  left / right  — switch pane focus
  q             — exit immediately
  ctrl+c        — push QuitScreen confirmation dialog
  ctrl+l        — clear both panes and reset
  r / c / x / y — review actions (only active during REVIEWING state)
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
    ReconciliationReady, ApplyResult,
)
from tui.session import SessionState
from tui.widgets.agent_pane import AgentPane
from tui.widgets.apply_confirm_screen import ApplyConfirmScreen
from tui.widgets.prompt_bar import PromptBar
from tui.widgets.quit_screen import QuitScreen
from tui.widgets.reconciliation_panel import ReconciliationPanel
from tui.widgets.review_bar import ReviewBar
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
        # Review actions — only honoured when session_state == REVIEWING
        Binding("r", "reconcile_again", "Reconcile again", show=False),
        Binding("c", "accept_claude", "Accept Claude", show=False),
        Binding("x", "accept_codex", "Accept Codex", show=False),
        Binding("y", "apply_reconciled", "Apply reconciled", show=False),
    ]

    session_state: reactive[SessionState] = reactive(SessionState.IDLE)

    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal():
            yield AgentPane(agent_name="claude", id="pane-left")
            yield Static("│", id="divider")
            yield AgentPane(agent_name="codex", id="pane-right")
        yield ReconciliationPanel(id="recon-panel")
        yield ReviewBar(id="review-bar")
        yield PromptBar(id="prompt-bar")

    def on_mount(self) -> None:
        self.query_one("#pane-left", AgentPane).focus()
        self._terminal_events: dict[str, BridgeEvent] = {}
        self._agent_line_counts: dict[str, int] = {"claude": 0, "codex": 0}
        self._last_texts: dict[str, str] = {}
        self._agreed_code: str = ""
        self._agreed_language: str = "python"
        self._agreed_filename: str | None = None

    def watch_session_state(self, state: SessionState) -> None:
        try:
            prompt_input = self.query_one("#prompt-input", Input)
            prompt_input.disabled = state != SessionState.IDLE
        except Exception:
            pass

    # --- Prompt submission ---

    def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt or self.session_state != SessionState.IDLE:
            return
        event.input.clear()
        self._start_session(prompt)

    def _start_session(self, prompt: str) -> None:
        self._terminal_events = {}
        self._agent_line_counts = {"claude": 0, "codex": 0}
        self._last_texts = {}
        self._agreed_code = ""
        self._agreed_language = "python"
        self._agreed_filename = None

        self.query_one("#recon-panel", ReconciliationPanel).hide_panel()
        self.query_one("#review-bar", ReviewBar).hide()

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
        """Worker: fan-out to both agents simultaneously, collect responses."""
        from tui.bridge import _stream_pipe, CLAUDE, CODEX

        q: asyncio.Queue[BridgeEvent] = asyncio.Queue()
        collected: dict[str, list[str]] = {"claude": [], "codex": []}

        task_a = asyncio.create_task(_stream_pipe(CLAUDE, prompt, 60.0, q))
        task_b = asyncio.create_task(_stream_pipe(CODEX, prompt, 60.0, q))

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

    # --- Message handlers ---

    def on_token_received(self, message: TokenReceived) -> None:
        pane_id = "#pane-left" if message.agent == "claude" else "#pane-right"
        pane = self.query_one(pane_id, AgentPane)
        pane.write_token(message.text)
        self._agent_line_counts[message.agent] = (
            self._agent_line_counts.get(message.agent, 0) + 1
        )
        self.query_one("#status-bar", StatusBar).show_streaming(self._agent_line_counts)

        left = self.query_one("#pane-left", AgentPane)
        right = self.query_one("#pane-right", AgentPane)
        if left.line_count >= SCROLLBACK_LIMIT or right.line_count >= SCROLLBACK_LIMIT:
            self.action_clear_panes()

    def on_agent_finished(self, message: AgentFinished) -> None:
        event = message.event
        pane_id = "#pane-left" if message.agent == "claude" else "#pane-right"
        pane = self.query_one(pane_id, AgentPane)

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
        from disagree_v1.classifier import classify_disagreements
        from disagree_v1.adapters import CommandJsonAdapter
        from disagree_v1.models import AgentResponse

        full_texts: dict[str, str] = {}
        responses: dict[str, AgentResponse] = {}

        for agent_name, event in self._terminal_events.items():
            if isinstance(event, AgentDone):
                full_texts[agent_name] = event.full_text
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
        """Apply classification visuals, then automatically start reconciliation."""
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.show_classification(self._agent_line_counts, message.disagreements)

        has_disagreements = bool(message.disagreements)
        self.query_one("#pane-left", AgentPane).set_disagreement_highlight(has_disagreements)
        self.query_one("#pane-right", AgentPane).set_disagreement_highlight(has_disagreements)

        # Merge full_texts into _last_texts (classification may have cleaner text)
        for agent, text in message.full_texts.items():
            if text:
                self._last_texts[agent] = text

        # Auto-start reconciliation — no user action required
        self.session_state = SessionState.RECONCILING
        self.query_one("#status-bar", StatusBar).show_reconciling()
        self.run_worker(
            self._run_reconciliation(),
            exclusive=False,
            exit_on_error=False,
            name="reconciliation",
        )

    async def _run_reconciliation(self) -> None:
        """Worker: send both responses to Claude for unified reconciliation."""
        from tui.bridge import _stream_pipe, CLAUDE
        from tui.apply import extract_code_proposals, generate_unified_diff

        claude_text = self._last_texts.get("claude", "")
        codex_text = self._last_texts.get("codex", "")

        recon_prompt = (
            f"Here is what Agent A (Claude) proposed:\n{claude_text}\n\n"
            f"Here is what Agent B (Codex) proposed:\n{codex_text}\n\n"
            f"These are complementary perspectives. Produce the best unified solution "
            f"that incorporates the strengths of both. "
            f"First write a brief plain-language explanation of how you merged the two approaches. "
            f"Then provide the final code in a fenced code block, with the target filename "
            f"as the first line comment (e.g. # src/module.py)."
        )

        from tui.event_bus import BridgeEvent as _BridgeEvent
        q: asyncio.Queue[_BridgeEvent] = asyncio.Queue()
        task = asyncio.create_task(_stream_pipe(CLAUDE, recon_prompt, 90.0, q))

        recon_tokens: list[str] = []
        while True:
            event = await q.get()
            if event.type == "token":
                recon_tokens.append(event.text)
            elif event.type in ("done", "error", "timeout"):
                break
        await task

        full_recon = "\n".join(recon_tokens)
        proposals = extract_code_proposals(full_recon)
        if proposals:
            agreed = proposals[-1]
            self._agreed_code = agreed.code
            self._agreed_language = agreed.language
            self._agreed_filename = agreed.filename
        else:
            self._agreed_code = ""
            self._agreed_language = "text"
            self._agreed_filename = None

        claude_proposals = extract_code_proposals(claude_text)
        original_code = claude_proposals[-1].code if claude_proposals else ""
        diff_text = generate_unified_diff(
            original_code, self._agreed_code,
            fromfile="claude", tofile="reconciled"
        )

        self.post_message(ReconciliationReady(
            discussion_text=full_recon,
            diff_text=diff_text,
            agreed_code=self._agreed_code,
            language=self._agreed_language,
        ))

    def on_reconciliation_ready(self, message: ReconciliationReady) -> None:
        """Show reconciliation panel and review bar."""
        self.query_one("#recon-panel", ReconciliationPanel).show_reconciliation(
            message.discussion_text, message.diff_text
        )
        self.session_state = SessionState.REVIEWING
        self.query_one("#status-bar", StatusBar).show_reviewing(self._agent_line_counts)
        self.query_one("#review-bar", ReviewBar).show()

    def on_apply_result(self, message: ApplyResult) -> None:
        if message.confirmed and message.files_written:
            status_text = f"Applied — wrote {len(message.files_written)} file(s): {', '.join(message.files_written)}"
        elif message.confirmed:
            status_text = "Applied — no files detected in reconciliation output"
        else:
            status_text = "Cancelled — no files written"

        self.query_one("#status-bar", StatusBar).update(status_text)
        self.query_one("#review-bar", ReviewBar).hide()
        self.session_state = SessionState.IDLE
        self.query_one("#prompt-input", Input).focus()

    # --- Review actions (only honoured during REVIEWING state) ---

    def action_reconcile_again(self) -> None:
        if self.session_state != SessionState.REVIEWING:
            return
        self.query_one("#review-bar", ReviewBar).hide()
        self.query_one("#recon-panel", ReconciliationPanel).hide_panel()
        self.session_state = SessionState.RECONCILING
        self.query_one("#status-bar", StatusBar).show_reconciling()
        self.run_worker(
            self._run_reconciliation(),
            exclusive=False,
            exit_on_error=False,
            name="reconciliation",
        )

    def action_accept_claude(self) -> None:
        if self.session_state != SessionState.REVIEWING:
            return
        self._set_agreed_from_agent("claude")
        self._start_apply()

    def action_accept_codex(self) -> None:
        if self.session_state != SessionState.REVIEWING:
            return
        self._set_agreed_from_agent("codex")
        self._start_apply()

    def action_apply_reconciled(self) -> None:
        if self.session_state != SessionState.REVIEWING:
            return
        self._start_apply()

    def _set_agreed_from_agent(self, agent: str) -> None:
        """Extract code proposals from one agent's response and store as agreed."""
        from tui.apply import extract_code_proposals
        text = self._last_texts.get(agent, "")
        proposals = extract_code_proposals(text)
        if proposals:
            agreed = proposals[-1]
            self._agreed_code = agreed.code
            self._agreed_language = agreed.language
            self._agreed_filename = agreed.filename
        else:
            self._agreed_code = ""
            self._agreed_language = "text"
            self._agreed_filename = None

    def _start_apply(self) -> None:
        self.query_one("#review-bar", ReviewBar).hide()
        file_count = 1 if self._agreed_filename else 0
        self.session_state = SessionState.CONFIRMING_APPLY
        self.query_one("#status-bar", StatusBar).show_apply_confirm(file_count)
        self.run_worker(
            self._apply_confirm_flow(),
            exclusive=False,
            exit_on_error=False,
            name="apply-confirm",
        )

    async def _apply_confirm_flow(self) -> None:
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

    # --- Standard actions ---

    def action_focus_left(self) -> None:
        self.query_one("#pane-left", AgentPane).focus()

    def action_focus_right(self) -> None:
        self.query_one("#pane-right", AgentPane).focus()

    def action_quit(self) -> None:
        self.exit()

    def action_confirm_quit(self) -> None:
        self.push_screen(QuitScreen(), lambda result: self.exit() if result else None)

    def action_clear_panes(self) -> None:
        self.query_one("#pane-left", AgentPane).clear()
        self.query_one("#pane-right", AgentPane).clear()
        self.query_one("#recon-panel", ReconciliationPanel).hide_panel()
        self.query_one("#review-bar", ReviewBar).hide()
        self._agent_line_counts = {"claude": 0, "codex": 0}
        self.query_one("#status-bar", StatusBar).show_hints()


def main() -> None:
    """Entry point for the `agent-bureau` CLI command."""
    AgentBureauApp().run()


if __name__ == "__main__":
    main()
