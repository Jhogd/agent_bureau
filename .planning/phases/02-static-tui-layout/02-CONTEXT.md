# Phase 2: Static TUI Layout - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a working terminal TUI with two named agent columns displayed side-by-side, each independently scrollable with syntax-highlighted content — all validated against placeholder content before any live agent subprocess is connected. No streaming, no real agents, no flow control in this phase.

</domain>

<decisions>
## Implementation Decisions

### Column layout
- 50/50 horizontal split — each agent pane gets equal width
- Columns separated by a single vertical line divider (box-drawing character, full height)
- Each column header shows agent name only (e.g., "claude", "codex") — clean and minimal
- Empty pane shows dimmed placeholder text (e.g., "Waiting for claude...") centered in the pane area

### Keyboard navigation
- Left/right arrow keys switch focus between the left and right pane
- Up/down arrow keys scroll the currently focused pane line by line
- Active pane indicated by a highlighted (brighter) agent name header; inactive header is dimmed
- Exit: `q` exits cleanly; Ctrl-C shows a confirmation prompt before exiting

### Syntax highlighting
- Code detection: fenced code blocks only (triple-backtick with language tag: ```python, ```js, etc.)
- Language support: detect from the language tag in the code fence — highlight whatever language is tagged
- Visual style: code blocks have a slightly dimmed background to visually separate them from prose text; code appears inset within the pane flow
- Inline code (single backticks): Claude's Discretion

### Claude's Discretion
- Inline code styling (single backticks) — Claude picks what looks cleanest
- Exact color values and theme (dark terminal assumed; color palette is open)
- Exact placeholder text wording for empty panes
- Page Up/Down support as a bonus scroll shortcut (arrow keys are required minimum)
- Scrollback buffer size (must be bounded — no OOM)

</decisions>

<specifics>
## Specific Ideas

- The feel should match watching `claude` or `codex` run in a real terminal — clean, minimal, terminal-native
- The layout is the skeleton that Phase 3 streams live content into; it must look production-ready even with placeholder text

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-static-tui-layout*
*Context gathered: 2026-02-22*
