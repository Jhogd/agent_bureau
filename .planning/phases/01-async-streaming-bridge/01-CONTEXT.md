# Phase 1: Async Streaming Bridge - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the async streaming bridge that fans out to exactly 2 agent subprocesses concurrently, streams their raw text output through a typed event queue, and reports errors cleanly. No TUI in this phase. The bridge is proven correct via a test harness with a fake AgentRunner before any TUI code exists.

Drop the old disagree_v1 JSON-over-subprocess approach entirely. The TUI is the product now.

</domain>

<decisions>
## Implementation Decisions

### Streaming granularity
- Use PTY (pseudo-terminal) to give each agent subprocess a fake terminal, so agents stream output exactly as they would in a real terminal (no buffering)
- Try PTY first; if PTY fails (e.g., in certain CI environments), fall back to piped mode with a warning — do not crash
- Preserve ANSI color codes from agent output; do not strip them. The TUI should render agent colors.
- Streaming chunk granularity: Claude's Discretion — pick whatever feels most natural in the pane (every raw chunk or complete lines)

### Error containment
- If one agent crashes or times out, the other agent's stream continues uninterrupted
- The failed agent's pane shows a clear error; the surviving agent finishes normally
- After one agent fails and the other finishes, user has both options: apply the surviving agent's answer as normal, OR retry the failed agent only
- Single global timeout applies to all agents (not per-agent config)

### Agent invocation
- Invoke agents with raw text output — no JSON wrapping, no `--output-format json`
- Invoke as a command-line argument: `claude "prompt"`, `codex "prompt"`, etc.
- The old disagree_v1 batch CLI and JSON schema are dropped — not maintained alongside the TUI
- How command templates are structured for the bridge (config vs hardcoded): Claude's Discretion — pick whatever makes Phase 1 testable and Phase 5 (agent discovery/config) easy to extend

### Concurrency model
- Exactly 2 agents — not generalized to N
- Both agents run in parallel from the moment the prompt is submitted
- Bridge waits for BOTH agents to finish streaming before running disagreement classification
- Classification happens once, on complete responses

</decisions>

<specifics>
## Specific Ideas

- Streaming should look and feel exactly like watching `claude` run in a terminal — the PTY approach is specifically chosen to match that experience
- The user explicitly dropped the N-agent generalization in favor of keeping it simple: exactly 2, always

</specifics>

<deferred>
## Deferred Ideas

- N-agent support (3+ agents) — considered and explicitly deferred; 2 agents is the v1 design
- Per-agent timeout configuration — deferred to config phase; single global timeout for v1

</deferred>

---

*Phase: 01-async-streaming-bridge*
*Context gathered: 2026-02-21*
