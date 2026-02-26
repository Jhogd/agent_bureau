"""AgentBureauApp — the main Textual application for Agent Bureau.

Layout (top to bottom):
  1. StatusBar (id="status-bar") — docked top
  2. Horizontal container with AgentPane x2 + divider — fills remaining height
  3. ReconciliationPanel (id="recon-panel") — hidden until reconciliation completes
  4. ReviewBar (id="review-bar") — hidden until reconciliation completes
  5. PromptBar (id="prompt-bar") — docked bottom

Flow:
  User submits prompt → both agents stream simultaneously → classification →
  auto-reconciliation (each agent sees the other's response and proposes a
  unified solution) → ReviewBar appears with options:
    [r] Reconcile further  [c] Apply Claude  [x] Apply Codex

  "Reconcile further" feeds the reconciliation outputs back as new inputs,
  so each subsequent round is cross-reviewing the previous reconciliation.

Keyboard bindings:
  left / right        — switch pane focus
  ctrl+left/right     — shift horizontal divider (±5 %)
  ctrl+up/down        — resize reconciliation panel (±2 rows)
  q                   — exit immediately
  ctrl+c              — push QuitScreen confirmation dialog
  ctrl+l              — clear both panes and reset
  r / c / x / y       — review actions (only active during REVIEWING state)
"""
from __future__ import annotations

import asyncio
import os
import subprocess
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
        # Pane resize
        Binding("ctrl+left", "pane_shift_left", "Divider left", show=False),
        Binding("ctrl+right", "pane_shift_right", "Divider right", show=False),
        Binding("ctrl+up", "recon_shrink", "Shrink recon", show=False),
        Binding("ctrl+down", "recon_grow", "Grow recon", show=False),
        # Review actions — only honoured when session_state == REVIEWING
        Binding("r", "reconcile_again", "Reconcile further", show=False),
        Binding("c", "accept_claude", "Apply Claude", show=False),
        Binding("x", "accept_codex", "Apply Codex", show=False),
        Binding("y", "merge_and_apply", "Merge & apply", show=False),
    ]

    session_state: reactive[SessionState] = reactive(SessionState.IDLE)
    # Horizontal split: left pane weight out of 100 (default 50/50)
    pane_split: reactive[int] = reactive(50)
    # Reconciliation panel height in rows
    recon_height: reactive[int] = reactive(15)

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
        self._recon_proposals: dict[str, object] = {"claude": None, "codex": None}
        self._agreed_code: str = ""
        self._agreed_language: str = "python"
        self._agreed_filename: str | None = None

    def watch_session_state(self, state: SessionState) -> None:
        try:
            prompt_input = self.query_one("#prompt-input", Input)
            prompt_input.disabled = state != SessionState.IDLE
        except Exception:
            pass

    def watch_pane_split(self, split: int) -> None:
        try:
            self.query_one("#pane-left").styles.width = f"{split}fr"
            self.query_one("#pane-right").styles.width = f"{100 - split}fr"
        except Exception:
            pass

    def watch_recon_height(self, height: int) -> None:
        try:
            self.query_one("#recon-panel").styles.height = height
        except Exception:
            pass

    # --- Environment context ---

    @staticmethod
    def _gather_env_context() -> str:
        """Collect cwd, git branch, and top-level project structure.

        Returns a compact multi-line string suitable for prepending to user
        prompts so both agents understand the environment they are operating in.
        Returns an empty string if nothing useful can be gathered.
        """
        lines: list[str] = []

        cwd = os.getcwd()
        lines.append(f"Working directory: {cwd}")

        try:
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                text=True, stderr=subprocess.DEVNULL,
            ).strip()
            if branch:
                lines.append(f"Git branch: {branch}")
        except Exception:
            pass

        try:
            remote = subprocess.check_output(
                ["git", "remote", "get-url", "origin"],
                text=True, stderr=subprocess.DEVNULL,
            ).strip()
            if remote:
                lines.append(f"Git remote: {remote}")
        except Exception:
            pass

        try:
            _SKIP = {"__pycache__", "node_modules", ".git", ".venv", "venv", ".mypy_cache"}
            entries = sorted(
                e for e in os.listdir(cwd)
                if e not in _SKIP and not (e.startswith(".") and e not in {".planning"})
            )
            if entries:
                lines.append(f"Project root: {', '.join(entries[:30])}")
        except Exception:
            pass

        return "\n".join(lines)

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
        self._recon_proposals = {"claude": None, "codex": None}
        self._agreed_code = ""
        self._agreed_language = "python"
        self._agreed_filename = None

        self.query_one("#recon-panel", ReconciliationPanel).hide_panel()
        self.query_one("#review-bar", ReviewBar).hide()

        separator = "\u2500" * 60
        self.query_one("#pane-left", AgentPane).write_token(separator)
        self.query_one("#pane-right", AgentPane).write_token(separator)

        self.query_one("#pane-left", AgentPane).show_loading()
        self.query_one("#pane-right", AgentPane).show_loading()
        self.session_state = SessionState.STREAMING
        env_ctx = self._gather_env_context()
        full_prompt = f"## Environment\n{env_ctx}\n\n## Task\n{prompt}" if env_ctx else prompt
        self.run_worker(
            self._run_session(full_prompt),
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
        # Don't overwrite "Reconciling..." status bar while reconciliation is streaming
        if self.session_state != SessionState.RECONCILING:
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
        self.query_one("#pane-left", AgentPane).show_loading()
        self.query_one("#pane-right", AgentPane).show_loading()
        self.run_worker(
            self._run_reconciliation(),
            exclusive=False,
            exit_on_error=False,
            name="reconciliation",
        )

    async def _run_reconciliation(self) -> None:
        """Worker: each agent sees the other's response and proposes a unified solution.

        Both reconciliation responses stream to their respective panes (with a
        separator line). After both finish, _last_texts is updated to the
        reconciliation outputs so that 'reconcile further' naturally feeds those
        into the next round.
        """
        from tui.bridge import _stream_pipe, CLAUDE, CODEX
        from tui.apply import extract_code_proposals, generate_unified_diff

        claude_text = self._last_texts.get("claude", "")
        codex_text = self._last_texts.get("codex", "")

        separator = "\u2500" * 60
        self.post_message(TokenReceived(agent="claude", text=separator))
        self.post_message(TokenReceived(agent="codex", text=separator))

        claude_prompt = (
            f"You previously proposed:\n{claude_text}\n\n"
            f"Here is what Codex proposed:\n{codex_text}\n\n"
            f"Review both approaches. Identify the strengths of each and produce "
            f"the best unified solution. Write a brief explanation, then provide "
            f"the final code in a fenced block with the target filename as the "
            f"first line comment (e.g. # src/module.py)."
        )
        codex_prompt = (
            f"You previously proposed:\n{codex_text}\n\n"
            f"Here is what Claude proposed:\n{claude_text}\n\n"
            f"Review both approaches. Identify the strengths of each and produce "
            f"the best unified solution. Write a brief explanation, then provide "
            f"the final code in a fenced block with the target filename as the "
            f"first line comment (e.g. # src/module.py)."
        )

        q: asyncio.Queue[BridgeEvent] = asyncio.Queue()
        collected: dict[str, list[str]] = {"claude": [], "codex": []}

        task_a = asyncio.create_task(_stream_pipe(CLAUDE, claude_prompt, 90.0, q))
        task_b = asyncio.create_task(_stream_pipe(CODEX, codex_prompt, 90.0, q))

        terminal_count = 0
        while terminal_count < 2:
            event = await q.get()
            if event.type == "token":
                self.post_message(TokenReceived(agent=event.agent, text=event.text))
                collected[event.agent].append(event.text)
            elif event.type in ("done", "error", "timeout"):
                terminal_count += 1

        await asyncio.gather(task_a, task_b)

        recon_claude = "\n".join(collected["claude"])
        recon_codex = "\n".join(collected["codex"])

        # Update _last_texts so "reconcile further" builds on these outputs
        self._last_texts = {"claude": recon_claude, "codex": recon_codex}

        # Extract code proposals for apply actions
        claude_proposals = extract_code_proposals(recon_claude)
        codex_proposals = extract_code_proposals(recon_codex)
        self._recon_proposals = {
            "claude": claude_proposals[-1] if claude_proposals else None,
            "codex": codex_proposals[-1] if codex_proposals else None,
        }

        # Diff between the two reconciliation proposals
        claude_code = self._recon_proposals["claude"].code if self._recon_proposals["claude"] else recon_claude
        codex_code = self._recon_proposals["codex"].code if self._recon_proposals["codex"] else recon_codex
        diff_text = generate_unified_diff(
            claude_code, codex_code,
            fromfile="claude-recon", tofile="codex-recon"
        )

        self.post_message(ReconciliationReady(diff_text=diff_text))

    def on_reconciliation_ready(self, message: ReconciliationReady) -> None:
        """Show reconciliation panel and review bar."""
        code_found = (
            self._recon_proposals.get("claude") is not None
            or self._recon_proposals.get("codex") is not None
        )
        self.query_one("#recon-panel", ReconciliationPanel).show_reconciliation(
            message.diff_text, code_found=code_found
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
        self.query_one("#pane-left", AgentPane).show_loading()
        self.query_one("#pane-right", AgentPane).show_loading()
        self.run_worker(
            self._run_reconciliation(),
            exclusive=False,
            exit_on_error=False,
            name="reconciliation",
        )

    def action_accept_claude(self) -> None:
        if self.session_state != SessionState.REVIEWING:
            return
        proposal = self._recon_proposals.get("claude")
        if proposal is not None:
            self._agreed_code = proposal.code
            self._agreed_language = proposal.language
            self._agreed_filename = proposal.filename
        else:
            self._agreed_code = self._last_texts.get("claude", "")
            self._agreed_language = "text"
            self._agreed_filename = None
        self._start_apply()

    def action_accept_codex(self) -> None:
        if self.session_state != SessionState.REVIEWING:
            return
        proposal = self._recon_proposals.get("codex")
        if proposal is not None:
            self._agreed_code = proposal.code
            self._agreed_language = proposal.language
            self._agreed_filename = proposal.filename
        else:
            self._agreed_code = self._last_texts.get("codex", "")
            self._agreed_language = "text"
            self._agreed_filename = None
        self._start_apply()

    def action_merge_and_apply(self) -> None:
        """Merge both reconciliation outputs via a single Claude call, then apply."""
        if self.session_state != SessionState.REVIEWING:
            return
        self.query_one("#review-bar", ReviewBar).hide()
        self.session_state = SessionState.RECONCILING
        self.query_one("#status-bar", StatusBar).update("Merging — producing final unified solution...")
        self.run_worker(
            self._run_merge_and_apply(),
            exclusive=False,
            exit_on_error=False,
            name="merge-apply",
        )

    async def _run_merge_and_apply(self) -> None:
        """Worker: single Claude call that merges both recon outputs into one result."""
        from tui.bridge import _stream_pipe, CLAUDE
        from tui.apply import extract_code_proposals

        claude_recon = self._last_texts.get("claude", "")
        codex_recon = self._last_texts.get("codex", "")

        merge_prompt = (
            f"Here are two reconciled solutions from two AI agents:\n\n"
            f"## Claude's reconciliation\n{claude_recon}\n\n"
            f"## Codex's reconciliation\n{codex_recon}\n\n"
            f"Produce one definitive unified solution that takes the best of both. "
            f"Write a one-sentence rationale, then provide the final code in a "
            f"fenced block with the target filename as the first line comment."
        )

        q: asyncio.Queue[BridgeEvent] = asyncio.Queue()
        task = asyncio.create_task(_stream_pipe(CLAUDE, merge_prompt, 90.0, q))

        merged_tokens: list[str] = []
        while True:
            event = await q.get()
            if event.type == "token":
                merged_tokens.append(event.text)
            elif event.type in ("done", "error", "timeout"):
                break
        await task

        merged_text = "\n".join(merged_tokens)
        proposals = extract_code_proposals(merged_text)
        if proposals:
            best = proposals[-1]
            self._agreed_code = best.code
            self._agreed_language = best.language
            self._agreed_filename = best.filename
        else:
            self._agreed_code = merged_text
            self._agreed_language = "text"
            self._agreed_filename = None

        # Show the merged output in the reconciliation panel for review
        self.query_one("#recon-panel", ReconciliationPanel).show_merge_output(merged_text)
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

        # Use fallback filename when agents omit the filename comment
        target_filename = self._agreed_filename
        if not target_filename and self._agreed_code.strip():
            _ext = {"python": "py", "javascript": "js", "typescript": "ts",
                    "go": "go", "rust": "rs", "java": "java", "ruby": "rb",
                    "bash": "sh", "shell": "sh"}.get(self._agreed_language, "txt")
            target_filename = f"output.{_ext}"

        confirmed: bool = await self.push_screen(
            ApplyConfirmScreen(filename=target_filename, code=self._agreed_code),
            wait_for_dismiss=True,
        )
        files_written: list[str] = []
        if confirmed and target_filename and self._agreed_code.strip():
            target = Path(target_filename)
            write_file_atomic(target, self._agreed_code)
            files_written.append(str(target))
        self.post_message(ApplyResult(confirmed=confirmed, files_written=files_written))

    # --- Resize actions ---

    def action_pane_shift_left(self) -> None:
        self.pane_split = max(10, self.pane_split - 5)

    def action_pane_shift_right(self) -> None:
        self.pane_split = min(90, self.pane_split + 5)

    def action_recon_shrink(self) -> None:
        self.recon_height = max(4, self.recon_height - 2)

    def action_recon_grow(self) -> None:
        self.recon_height = min(50, self.recon_height + 2)

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
