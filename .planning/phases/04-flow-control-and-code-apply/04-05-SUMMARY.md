---
phase: 04-flow-control-and-code-apply
plan: "05"
subsystem: tui-app
tags: [integration, flow-control, debate, reconciliation, apply, textual]
dependency_graph:
  requires:
    - 04-01  # Phase 4 messages and SessionState
    - 04-02  # Modal screens (FlowPickerScreen, WinnerPickerScreen, etc.)
    - 04-03  # apply.py (extract_code_proposals, generate_unified_diff, write_file_atomic)
    - 04-04  # ReconciliationPanel, StatusBar Phase 4 methods
  provides:
    - AgentBureauApp fully integrated with Phase 4 flow control and code apply
  affects:
    - src/tui/app.py
    - tests/tui/test_app.py
tech_stack:
  added: []
  patterns:
    - Worker coroutine pattern for push_screen(wait_for_dismiss=True)
    - Callback pattern for action_* handlers (cannot use wait_for_dismiss)
    - Post-message pattern for async worker -> UI communication (thread safety)
    - asyncio.Event for debate stop signal (_debate_stop)
key_files:
  modified:
    - src/tui/app.py
    - tests/tui/test_app.py
decisions:
  - "watch_session_state updated to disable input for all non-IDLE states (not just STREAMING/CLASSIFYING) — simpler and correct for Phase 4"
  - "action_end_debate uses callback form push_screen (not await) — action_* handlers cannot use wait_for_dismiss=True per RESEARCH.md"
  - "Static.render() used for status bar text assertions in tests (not .renderable which was removed in Textual 8.x)"
  - "_run_reconciliation imports CLAUDE only — reconciliation pass always uses Claude as the arbitrator"
  - "_debate_stop.clear() called both in on_mount and at start of _run_live_debate for safety"
metrics:
  duration: "~9 min"
  completed: 2026-02-24
  tasks_completed: 2
  files_modified: 2
---

# Phase 4 Plan 05: AgentBureauApp Phase 4 Integration Summary

AgentBureauApp wired with full Phase 4 flow: FlowPickerScreen gate, pick-one and live-debate routing, debate loop with Esc stop, WinnerPickerScreen, collaborative reconciliation pass, ReconciliationPanel display, and ApplyConfirmScreen file-write gate.

## What Was Built

### Task 1: Extend AgentBureauApp with Phase 4 flow control and apply

Extended `src/tui/app.py` with the following new methods and changes:

**New async worker methods:**
- `_run_session`: Replaced with flow-picker-first version; awaits FlowPickerScreen and routes to pick-one or live-debate
- `_run_pick_one`: Fan-out to both agents, collects responses, posts DebateEnded
- `_run_live_debate`: Up to MAX_ROUNDS=3 rounds with RoundBoundary markers and _debate_stop check
- `_run_reconciliation`: Feeds both proposals to Claude with collaborative framing; extracts agreed code and diff
- `_pick_winner_flow`: Shows WinnerPickerScreen; handles keep-discussing by re-prompting; routes to reconciliation
- `_apply_confirm_flow`: Shows ApplyConfirmScreen; calls write_file_atomic on confirm; posts ApplyResult

**New message handlers:**
- `on_round_boundary`: Inserts round divider text into both panes
- `on_debate_ended`: Transitions to PICK_WINNER, updates status bar, launches _pick_winner_flow worker
- `on_reconciliation_ready`: Makes ReconciliationPanel visible, transitions to CONFIRMING_APPLY, launches _apply_confirm_flow worker
- `on_apply_result`: Updates status bar with outcome, returns to IDLE, refocuses prompt input

**New action:**
- `action_end_debate`: Esc key during DEBATING; pushes ConfirmEndDebateScreen with callback; sets _debate_stop on confirm

**Modified:**
- `compose()`: Added `ReconciliationPanel(id="recon-panel")` between panes and prompt bar
- `on_mount()`: Added Phase 4 state fields (_debate_stop, _last_texts, _agreed_code, _agreed_language, _agreed_filename)
- `watch_session_state()`: Updated to disable input for all non-IDLE states (simplified from STREAMING/CLASSIFYING only)
- `_start_session()`: Added Phase 4 state reset, hides ReconciliationPanel, sets FLOW_PICK state

**BINDINGS updated:** Added `Binding("escape", "end_debate", "End debate", show=False)`

### Task 2: Integration tests for Phase 4 flows

Added 9 new integration tests to `tests/tui/test_app.py`:

1. `test_flow_picker_state_set_on_session_start` — FLOW_PICK state set; input disabled
2. `test_round_boundary_inserts_divider` — RoundBoundary message writes to both panes
3. `test_debate_ended_transitions_to_pick_winner_state` — DebateEnded sets PICK_WINNER
4. `test_debate_ended_updates_status_bar` — Status bar shows "Pick winner" text
5. `test_reconciliation_ready_shows_panel` — ReconciliationPanel becomes visible (display=True)
6. `test_apply_result_confirmed_returns_to_idle` — ApplyResult(confirmed=True) → IDLE
7. `test_apply_result_confirmed_shows_applied_in_status` — Status bar contains "Applied"
8. `test_apply_result_rejected_returns_to_idle` — ApplyResult(confirmed=False) → IDLE
9. `test_apply_result_rejected_shows_cancelled_in_status` — Status bar contains "Cancelled"

All 126 tests pass (117 prior + 9 new).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed status bar text assertion using wrong API**
- **Found during:** Task 2
- **Issue:** Tests used `status_bar.renderable` which does not exist in Textual 8.x Static widget
- **Fix:** Changed to `str(status_bar.render())` which returns the Content object and `str()` gives the text — consistent with `str(header.render())` pattern used in test_agent_pane.py
- **Files modified:** tests/tui/test_app.py
- **Commit:** d14797a

**2. [Rule 2 - Missing functionality] Added 3 extra status bar text tests**
- **Found during:** Task 2 planning
- **Issue:** Plan specified 6 tests but the test_debate_ended and test_apply_result tests each had a state check and a status bar text check as separate concerns; splitting them makes tests smaller and more focused (per SRP)
- **Fix:** Added 3 additional tests (status bar text assertions separated from state assertions)
- **Files modified:** tests/tui/test_app.py
- **Commit:** d14797a

## Commits

| Hash | Message |
|------|---------|
| 26ddea1 | feat(04-05): extend AgentBureauApp with Phase 4 flow control and apply |
| d14797a | test(04-05): add Phase 4 integration tests for flow control and apply |

## Self-Check: PASSED

All files present. All commits verified. 126 tests passing.
