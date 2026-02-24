# Phase 4: Flow Control and Code Apply - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can choose their session flow before agents run, watch a live debate with round-by-round streaming, pick a winner, and apply that agent's proposed file changes only after reviewing a reconciliation and confirming. Creating/discovering agents and packaging are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Flow-picker modal
- Appears as a slim top-banner prompt, not a full-screen overlay or centered dialog
- Navigation: arrow keys to move between options, Enter to confirm
- Default selection: pick-one is pre-highlighted (fastest common path)
- Ctrl-C quits the app from the flow-picker (standard exit, no forced flow choice)

### Live-debate round control
- Round boundaries are marked by a horizontal divider line inserted into each agent pane (e.g. `── Round 2 ──`)
- User ends the debate early with Esc
- Pressing Esc shows a confirm prompt before stopping ("End debate? [y/n]"), then moves to pick-winner
- Max rounds: Claude's discretion (pick a sensible default during planning)

### Pick-winner UX
- Pick-winner appears after both agents finish streaming (not mid-stream)
- Four-option menu (top-banner or overlay):
  1. Agent A wins
  2. Agent B wins
  3. Keep discussing (returns to debate)
  4. Cancel (clears context, no files written)
- No extra pane highlight — the four-option menu is sufficient

### Agent reconciliation and code apply
- When an agent wins (or debate ends), both agents are fed each other's proposals and produce a plain-language discussion of differences and how to reconcile
- Agents converge on agreed code changes through this discussion
- User sees: the agents' plain-language reconciliation discussion + the final agreed code block in the preview pane (overlay/panel below existing panes)
- Diff format: unified diff (standard -/+ lines) for any code shown
- Confirmation gate: user presses y to write, n to reject — single y/n covers all files at once
- No file is ever written without the explicit y confirmation

### Claude's Discretion
- Max rounds default in live-debate mode
- Exact reconciliation prompt design (how agents are instructed to compare and converge)
- How partial/failed reconciliation is handled (agents can't agree)
- Temp file handling during apply

</decisions>

<specifics>
## Specific Ideas

- Agents should discuss differences like collaborators, not adversaries — the reconciliation is about reaching the best outcome, not winning
- The agent reconciliation + agreed code display should feel like a natural continuation of the debate, not a separate "apply UI"
- Agents write files to disk the way they normally do (via their standard tool use) — the confirmation gate intercepts before actual disk write

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-flow-control-and-code-apply*
*Context gathered: 2026-02-24*
