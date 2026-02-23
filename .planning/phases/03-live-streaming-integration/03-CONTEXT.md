# Phase 3: Live Streaming Integration - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the async bridge (Phase 1) to the TUI (Phase 2) so real agent tokens stream into the correct labeled panes in real time. Add a prompt input bar, a live status bar, and disagreement indicators. Agents speak — the TUI listens and displays. Flow control (pick-winner, live-debate mode) and code apply are Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Prompt input
- Input field in the TUI — not a CLI argument
- Fixed one-line bar at the bottom of the screen (below agent panes)
- Layout from top to bottom: status bar / agent panes / prompt input
- Input is blocked/disabled while agents are streaming — no mid-run resubmit
- On new prompt submission: append output below the previous run's content with a visual separator
- Auto-clear panes when content approaches the scrollback limit (5000 lines)
- User can manually clear pane content via a keybinding (e.g., Ctrl-L)

### Status bar
- Sits at the very top of the screen, above the agent pane headers
- Shows: per-agent streaming state + token/line counts per agent + disagreement state
- Does NOT show elapsed time
- Initial state (before any prompt): keyboard hints (e.g., "Enter: submit • Ctrl-C: quit • Ctrl-L: clear")
- While streaming: "claude: streaming (42 lines) • codex: streaming (38 lines)"
- After both finish: completion summary (e.g., "Both done — claude: 120 lines, codex: 115 lines")
- After classification: adds disagreement or agreement result to the completion summary

### Disagreement display
- Status bar shows disagreement type label
- Both pane headers get a visual highlight when a disagreement is detected (color change or indicator)
- Classification runs once, after both agents finish streaming — no mid-stream classification
- Level of detail in status bar: Claude's Discretion (fit to available space)
- When agents agree: show explicit "agents agree" confirmation in status bar
- When agents disagree: show type label, e.g., "disagreement: approach"

### Streaming behavior
- Token-by-token: each token appended to the pane as soon as it arrives
- Agent errors: append a visible error message to the pane content (e.g., "[error: agent exited with code 1]")
- When one agent finishes and the other is still streaming: finished pane just stops — no done marker appended
- User can scroll any pane freely at any time during streaming; new tokens continue appending at the bottom

### Claude's Discretion
- Exact disagreement detail format in the status bar (type label vs type + description — fit to space)
- Run separator visual between successive prompt runs
- Keybinding for manual clear (Ctrl-L suggested but open)
- Auto-scroll behavior when user has scrolled up (standard Textual auto_scroll behavior)

</decisions>

<specifics>
## Specific Ideas

- Pane content persists across runs (append model) — user can review previous runs by scrolling up
- SCROLLBACK_LIMIT (5000) from Phase 2 is the auto-clear threshold — reuse the existing constant
- Both panes clear together when either hits the limit (keep them synchronized)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-live-streaming-integration*
*Context gathered: 2026-02-23*
