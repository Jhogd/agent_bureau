---
phase: 03-live-streaming-integration
plan: "02"
subsystem: ui
tags: [textual, richlog, ansi, streaming, tdd]

# Dependency graph
requires:
  - phase: 02-static-tui-layout
    provides: AgentPane widget with write_content() and RichLog composition
provides:
  - AgentPane.write_token() for per-token ANSI-decoded streaming writes
  - AgentPane.line_count property tracking tokens written
  - AgentPane.clear() to reset pane to initial placeholder state
  - AgentPane.set_disagreement_highlight() CSS class toggle for classification UI
affects:
  - 03-live-streaming-integration (plans 03, 04 — bridge and app wiring)
  - Phase 5 (subprocess integration that calls write_token per streamed chunk)

# Tech tracking
tech-stack:
  added: [rich.ansi.AnsiDecoder, rich.text.Text]
  patterns: [TDD Red-Green, ANSI decoding before RichLog write, class-level shared decoder instance]

key-files:
  created: []
  modified:
    - src/tui/widgets/agent_pane.py
    - tests/tui/test_agent_pane.py

key-decisions:
  - "write_token() is a separate method from write_content() — per-token streaming must not reuse the multi-line block path with fenced-code parsing"
  - "_ansi_decoder is a class-level AnsiDecoder instance shared across all AgentPane instances — avoids repeated instantiation per token"
  - "next(..., Text(line)) fallback ensures empty lines do not crash the ANSI decode generator"
  - "line_count tracks write_token() calls only, not write_content() — deliberate separation of streaming vs block write paths"

patterns-established:
  - "ANSI decode pattern: next(decoder.decode(line), Text(line)) — safe generator consumption with fallback"
  - "Pane state management: _has_content flag controls placeholder/log visibility on first write; clear() fully resets it"
  - "CSS highlight toggle: add_class/remove_class on the widget itself, driven by boolean param"

requirements-completed: [TUI-03]

# Metrics
duration: 2min
completed: 2026-02-23
---

# Phase 3 Plan 02: AgentPane Streaming Extensions Summary

**write_token() with AnsiDecoder, line_count property, clear() reset, and disagreement CSS highlight added to AgentPane via TDD (10 tests green)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-23T00:08:30Z
- **Completed:** 2026-02-23T00:10:06Z
- **Tasks:** 2 (RED + GREEN TDD cycle)
- **Files modified:** 2

## Accomplishments
- Extended AgentPane with a dedicated per-token streaming write path that decodes ANSI before writing to RichLog
- Added line_count property giving status bar consumers a cheap token count without querying DOM
- Added clear() to fully reset pane to placeholder state for session reuse
- Added set_disagreement_highlight() CSS toggle for classification result UI feedback
- 5 new tests extend the existing 5-test suite; all 67 project tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Failing tests for AgentPane streaming extensions** - `e1f5a68` (test)
2. **Task 2: GREEN — Implement write_token(), line_count, clear(), set_disagreement_highlight()** - `1366f34` (feat)

_Note: TDD tasks each have one commit (test → feat; no refactor needed)_

## Files Created/Modified
- `src/tui/widgets/agent_pane.py` - Added AnsiDecoder import, _ansi_decoder class attr, _line_count init, line_count property, write_token(), clear(), set_disagreement_highlight()
- `tests/tui/test_agent_pane.py` - Added Label import; appended 5 new async tests for streaming extensions

## Decisions Made
- `write_token()` does NOT call `write_content()` internally — the block-write path with fenced code detection is wrong for per-token streaming; methods are intentionally separate.
- `_ansi_decoder = AnsiDecoder()` is a class-level attribute so the same decoder instance is reused across all panes and all tokens without repeated construction overhead.
- `next(self._ansi_decoder.decode(line), Text(line))` pattern: `decode()` returns a generator; calling `next()` with a `Text` fallback safely handles empty strings without raising `StopIteration`.
- New tests use `id="pane"` (matching existing `PaneTestApp`), not `#pane-left` as shown in plan snippet — adjusted to match actual test fixture to avoid breaking existing tests.

## Deviations from Plan

**Minor adjustment:** Plan code snippet referenced `app.query_one("#pane-left", AgentPane)` in all new tests, but the existing `PaneTestApp` fixture uses `id="pane"`. Using `#pane-left` would cause `NoMatches` at runtime. New tests use `id="pane"` to match the fixture. This is a correction in the plan's example code, not a scope change.

**Total deviations:** 1 (plan snippet ID corrected — no production code impact)
**Impact on plan:** Purely a test fixture alignment fix. All behavior tested as specified.

## Issues Encountered
None — implementation matched plan exactly once the test fixture ID was corrected.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `AgentPane` now has the full streaming interface needed by 03-03 (bridge integration)
- `write_token()` is the target method for streamed output chunks from the async bridge
- `line_count` is ready for status bar display in 03-04
- `clear()` is ready for session reset in AgentBureauApp
- `set_disagreement_highlight()` is ready for the classification result display in Phase 5

---
*Phase: 03-live-streaming-integration*
*Completed: 2026-02-23*
