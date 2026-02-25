---
status: investigating
trigger: "Two bugs in the TUI after Phase 4 implementation: (1) prompt input field is too small/hard to see, (2) Claude streaming output looks like gibberish and the prompt text appears to replay multiple times during streaming"
created: 2026-02-24T00:00:00Z
updated: 2026-02-24T00:00:00Z
---

## Current Focus

hypothesis: Unknown — gathering initial evidence from codebase
test: Read app.py, widget code, streaming worker to understand current wiring
expecting: Find layout config for prompt widget size, and find streaming/display logic that may be corrupting output
next_action: Read src/tui/app.py and relevant widget files

## Symptoms

expected: Prompt input field should be clearly visible and usable. Claude's streaming output should show clean text tokens as they arrive.
actual: (1) Prompt field is way too small and hard to see. (2) Claude's response looks mostly like gibberish, the prompt appears to replay multiple times, and the output seemed erratic. Eventually something resembling a real response appeared but it was mixed with garbage.
errors: No explicit error messages reported — visual/display corruption
reproduction: Launch the TUI with `python -m tui.app`, type a prompt, press Enter, observe the prompt field size and the streaming output in the agent panes.
started: Observed during Phase 4 checkpoint verification. Phase 3 may have had working streaming — Phase 4 wiring added in 04-05 changed app.py significantly.

## Eliminated

(none yet)

## Evidence

(none yet)

## Resolution

root_cause:
fix:
verification:
files_changed: []
