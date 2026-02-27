# Agent Bureau

A terminal UI for side-by-side AI agent collaboration. Broadcasts a prompt to Claude and Codex simultaneously, streams their responses in parallel, automatically reconciles disagreements, and lets you apply the resulting code directly to your project.

## What it does

1. **Stream** — Both agents receive your prompt at the same time and stream responses into side-by-side panes.
2. **Classify** — Disagreements between agents are automatically detected and highlighted.
3. **Reconcile** — Each agent cross-reviews the other's response and proposes a unified solution.
4. **Review** — A diff panel shows the gap between the two reconciled proposals.
5. **Apply** — Pick one agent's answer, merge both, or reconcile again — then write the result to a file atomically.

## Requirements

- Python 3.10+
- [`claude`](https://claude.ai/code) CLI installed and authenticated
- [`codex`](https://github.com/openai/codex) CLI installed and authenticated

## Install

```bash
pip install -e ".[dev]"
```

## Launch

```bash
agent-bureau
```

Or directly:

```bash
python -m tui.app
```

## Layout

```
┌─ status bar ──────────────────────────────────────────────────┐
│ Claude                     │ Codex                            │
│                            │                                  │
│  (streaming response)      │  (streaming response)            │
│                            │                                  │
├─ reconciliation panel ─────────────────────────────────────────┤
│  diff between reconciled proposals                            │
├─ review bar ───────────────────────────────────────────────────┤
│  [r] Reconcile  [c] Apply Claude  [x] Apply Codex  [y] Merge  │
├─ prompt bar ───────────────────────────────────────────────────┤
│  > type your prompt here                                      │
└───────────────────────────────────────────────────────────────┘
```

## Workflow

1. Type a prompt and press `Enter`.
2. Both agents stream responses simultaneously into their panes.
3. Disagreements are detected automatically — pane headers turn yellow if agents disagree.
4. Reconciliation starts automatically: each agent reviews the other's output and proposes a unified solution.
5. The reconciliation panel shows a unified diff between the two proposals.
6. Choose what to do from the review bar:
   - `r` — reconcile again (feeds reconciliation outputs back for another round)
   - `c` — apply Claude's reconciled answer
   - `x` — apply Codex's reconciled answer
   - `y` — merge both via a final Claude call, then apply
7. A confirmation screen shows the filename and code before writing.

## Keyboard bindings

| Key | Action |
|-----|--------|
| `Enter` | Submit prompt |
| `r` | Reconcile further (during review) |
| `c` | Apply Claude's answer |
| `x` | Apply Codex's answer |
| `y` | Merge both and apply |
| `left` / `right` | Switch pane focus |
| `ctrl+left` / `ctrl+right` | Shift the vertical divider (±5%) |
| `ctrl+up` / `ctrl+down` | Resize reconciliation panel (±2 rows) |
| `ctrl+l` | Clear both panes and reset |
| `ctrl+c` | Quit confirmation dialog |
| `q` | Quit immediately |

## Run tests

```bash
source .venv/bin/activate
pytest tests/ -q
```

## Project structure

```
src/
  tui/
    app.py                     # Main Textual application and session orchestration
    bridge.py                  # Async subprocess fan-out to agent CLIs
    apply.py                   # Code extraction, diff generation, atomic file write
    session.py                 # Session state machine
    messages.py                # Textual message types for inter-component events
    event_bus.py               # Bridge event types (token, done, error, timeout)
    content.py                 # Scrollback limit constant
    widgets/
      agent_pane.py            # Scrollable pane for one agent's streamed output
      reconciliation_panel.py  # Below-panes diff and merge output panel
      review_bar.py            # Action hint bar shown during review
      status_bar.py            # Top status line
      prompt_bar.py            # Bottom prompt input
      apply_confirm_screen.py  # Modal confirmation before file write
      quit_screen.py           # Modal quit confirmation
  disagree_v1/                 # Underlying disagreement classification library
    classifier.py
    models.py
    orchestrator.py
    adapters.py
    adjudication.py
    store.py
```
