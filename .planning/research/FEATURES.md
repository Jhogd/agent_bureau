# FEATURES.md — Multi-Agent AI Coding CLI Orchestration Tool

**Research type:** Project Research — Features dimension
**Date:** 2026-02-21
**Milestone context:** Greenfield UX layer on top of existing orchestration core. Backend (parallel agent execution, disagreement classification, debate prompts) already exists. Building the user-facing interface and polish.

---

## Tool Landscape Survey

### Tools Examined

**aider**
- Terminal-based AI pair programmer. Works directly in the shell with git integration baked in.
- Key features: voice coding, multi-file editing, auto-commits after each change, architect mode (plan first) vs editor mode (apply only), map of entire codebase via repo-map, watch mode for continuous assistance, multiple model support.
- UX: pure terminal, no TUI chrome, relies on scrollback for context, diffs shown in unified diff format before applying.

**Claude Code (Anthropic)**
- Terminal agent with tool use: reads/writes files, runs shell commands, browses the web, executes tests.
- Key features: tool loop with confirmation prompts, streaming output, slash commands for workflow control, context window management, project-level CLAUDE.md instructions, MCP server integration.
- UX: conversational REPL, each tool call requires user approval (configurable), no side-by-side comparison of alternatives.

**Cursor**
- IDE fork (VS Code) with deep AI integration.
- Key features: inline diff application (Accept/Reject per hunk), Composer for multi-file changes, chat sidebar with codebase indexing, `@` symbol references for files/docs/web, rules files per project, background agent mode.
- UX: GUI-native, streaming diffs shown in-editor, visual accept/reject per change block.

**Continue.dev**
- VS Code/JetBrains extension. Open-source, model-agnostic.
- Key features: chat + edit modes, codebase indexing, slash commands for reusable prompts, context providers (`@file`, `@docs`, `@git`), multiple models switchable mid-session.
- UX: sidebar panel, inline edit suggestions, model picker.

**Multi-Agent Orchestration Tools (CrewAI, AutoGen, LangGraph, OpenHands)**
- CrewAI: role-based agents with defined tasks and sequential/parallel flows, human-in-the-loop checkpoints.
- AutoGen: conversation-based multi-agent, agents debate until consensus or turn limit, GroupChat manager routes messages.
- LangGraph: graph-based agent state machines, branching on conditions, human feedback nodes.
- OpenHands (formerly OpenDevin): web-browsing + coding agent with sandboxed execution, real-time action stream visible to user.
- UX varies: mostly logs/console output, minimal interactive TUI.

---

## Feature Categories

### TABLE STAKES
*Must have or users leave immediately. These are baseline expectations from any AI coding tool.*

| Feature | Description | Complexity | Dependencies |
|---|---|---|---|
| Streaming output | Agent responses render token-by-token, not batch | Low | Terminal rendering library (e.g., Bubble Tea / Rich) |
| Diff preview before apply | Show unified or side-by-side diff before writing to disk | Medium | Diff generation from agent output parser |
| Confirmation prompt | Explicit user approval before any file is written | Low | Diff preview |
| Keyboard-driven navigation | Arrow keys / vim bindings to move through UI | Low | TUI framework |
| Exit/cancel at any time | Ctrl-C or `q` always works cleanly without corrupting state | Low | Signal handling |
| Clear error messages | If an agent fails or times out, user knows what happened | Low | Error taxonomy |
| Show which agent produced which output | Labels or headers identifying the source agent per pane | Low | Agent metadata passed through to renderer |
| Scrollable output | Long agent responses are scrollable, not truncated | Low | TUI scrollview |
| Syntax highlighting | Code blocks highlighted by language | Low | Chroma / pygments integration |
| Respect terminal width | Layout adapts to 80/120/wider terminals | Low | TUI layout engine |

---

### DIFFERENTIATORS
*Competitive advantages specific to multi-agent orchestration. These are the reasons users choose this tool over aider or Claude Code alone.*

#### Core Multi-Agent UX (High Value, Medium-High Complexity)

| Feature | Description | Complexity | Dependencies |
|---|---|---|---|
| Side-by-side agent panes | Multiple agent responses displayed simultaneously in split-pane TUI | Medium | TUI framework, pane management, agent result buffering |
| Live debate view | Watch agents respond to each other's critiques in real time, streamed | High | Backend debate prompts (exists), streaming multiplexer, debate message router |
| Disagreement visualization | Highlight where agents diverge (different function names, different approaches) | High | Disagreement classifier (exists in backend), diff between agent outputs |
| Consensus indicator | Visual signal when agents reach agreement (e.g., progress bar, icon change) | Medium | Disagreement classifier output, state machine tracking convergence |
| Per-agent confidence / rationale display | Show each agent's reasoning summary alongside its code | Medium | Prompt engineering for rationale extraction, UI panel per agent |
| Agent identity system | Named, persistent agent personas (e.g., "Skeptic", "Implementer") with visual differentiation (color, icon) | Low | Config file or runtime assignment |
| Pick-winner UX | User selects which agent's solution to apply; chosen diff is applied, others discarded | Medium | Diff preview, file writer, selection state |
| Merge / hybrid apply | User can cherry-pick hunks from different agents and compose a final diff | High | Hunk-level selection UI, merge conflict resolver |
| Replay / audit trail | Persist the debate transcript so user can review agent reasoning after the fact | Medium | Structured log writer, optional replay mode |

#### Code Application UX (High Value, Medium Complexity)

| Feature | Description | Complexity | Dependencies |
|---|---|---|---|
| Hunk-level accept/reject (Cursor-style) | Accept or reject individual diff hunks within a chosen agent's output | High | Diff parser, per-hunk state, file writer |
| Auto-run tests after apply | Optionally run the project's test suite immediately after writing files | Medium | Shell executor, test runner detection (pytest, npm test, go test) |
| Git commit after apply | Optional automatic commit of applied changes with generated commit message | Low | git CLI, commit message generation prompt |
| Dry-run mode | Show all diffs that would be applied without touching disk | Low | File writer abstraction with dry-run flag |

#### Workflow UX (Medium Value, Low-Medium Complexity)

| Feature | Description | Complexity | Dependencies |
|---|---|---|---|
| Session persistence | Save and restore a multi-agent session (prompt, agent outputs, debate state) | Medium | Serialization format (JSON/SQLite), session manager |
| Prompt history | Navigate previous prompts with up-arrow (shell-style) | Low | In-memory ring buffer |
| Config file (`.agentbureau.toml` or similar) | Set default agents, model IDs, debate rounds, output directory | Low | TOML/YAML parser |
| Agent roster configuration | Add/remove agents from config; swap models at launch | Low | Config file |
| Progress indicators | Spinner or progress bar while agents are running in parallel | Low | TUI, async state tracking |
| Timeout + retry | Configurable per-agent timeout with automatic retry | Medium | Async executor, retry policy |

#### Observability / Trust (Medium Value, Medium Complexity)

| Feature | Description | Complexity | Dependencies |
|---|---|---|---|
| Token / cost display | Show estimated tokens used and cost per agent per session | Medium | Model pricing data, token counter |
| Latency display | Show how long each agent took to respond | Low | Timing instrumented in executor |
| Verbose / debug mode | Raw API payloads and debate prompts visible on request | Low | Log levels, flag |

---

### ANTI-FEATURES
*Things to deliberately NOT build in this milestone. Either out-of-scope, complexity sinkholes, or actively harmful to the tool's UX identity.*

| Anti-Feature | Reason to Avoid |
|---|---|
| GUI / Electron app | This is a CLI tool. GUI adds maintenance burden, deployment complexity, and abandons the power-user audience. Terminal is the identity. |
| Built-in model inference | Never host or run models. Call external CLIs/APIs only. Avoids GPU dependency, licensing, and infra costs. |
| Agent marketplace / plugin store | Premature ecosystem thinking. Get the core loop working first. |
| Real-time collaborative editing (multiplayer) | Scope explosion. Requires auth, sync, conflict resolution. Not the problem being solved. |
| Automatic code application without review | Always require explicit user confirmation. Removing the human in the loop destroys trust. |
| IDE extension version | Maintain focus. An IDE extension is a separate product with separate UX contracts. |
| Fine-tuning or training pipelines | Out of scope entirely. This tool consumes models, it does not train them. |
| Voice input | Distraction. Adds dependency, accessibility complexity, and is not a terminal-native interaction. |
| Automatic PR creation | Too opinionated about workflow. Offer git commit (optional), stop there. |
| Monolithic "super-agent" mode | The entire value proposition is multiple agents disagreeing. A single-agent mode undermines the product thesis. |
| Chat history UI (like Cursor sidebar) | This is a task-based tool, not a chat tool. Each invocation is a discrete coding task. Persistent chat history conflates the interaction model. |

---

## Feature Dependency Map

```
TUI Framework (Bubble Tea or similar)
├── Side-by-side panes
│   ├── Live debate view
│   │   └── Debate message router → [Backend debate prompts - EXISTS]
│   ├── Disagreement visualization → [Disagreement classifier - EXISTS]
│   └── Consensus indicator → [Disagreement classifier - EXISTS]
├── Diff preview before apply
│   ├── Hunk-level accept/reject
│   └── Pick-winner UX
│       └── File writer (dry-run capable)
│           ├── Auto-run tests after apply
│           └── Git commit after apply
├── Streaming output
│   └── Per-agent confidence / rationale display
└── Progress indicators
    └── Timeout + retry → [Async executor - EXISTS or near-exists]

Config file
├── Agent roster configuration
├── Per-agent timeout
└── Default debate rounds

Session persistence
└── Replay / audit trail
```

---

## Complexity Summary

| Complexity | Features |
|---|---|
| Low | Exit/cancel, keyboard nav, syntax highlighting, terminal width adaptation, error messages, agent labels, scrollable output, prompt history, config file, agent roster config, progress indicators, latency display, verbose mode, dry-run mode, git commit after apply, agent identity system, streaming output |
| Medium | Side-by-side panes, consensus indicator, per-agent rationale display, pick-winner UX, auto-run tests, session persistence, token/cost display, timeout + retry, replay / audit trail |
| High | Live debate view, disagreement visualization, hunk-level accept/reject, merge/hybrid apply |

---

## Recommended Build Order (for this milestone)

1. TUI framework selection and basic layout (table stakes unblock everything)
2. Side-by-side agent panes with streaming output and agent labels
3. Diff preview + pick-winner + file writer with confirmation
4. Live debate view (wires into existing backend)
5. Disagreement visualization + consensus indicator (wires into existing classifier)
6. Hunk-level accept/reject (high complexity, highest UX value after core loop)
7. Config file + agent roster
8. Auto-run tests, git commit, dry-run mode
9. Token/cost, latency display, verbose mode
10. Session persistence + replay (nice-to-have, defer if time-constrained)

---

*Sources: aider documentation and changelog (aider.chat), Cursor documentation (cursor.com/docs), Continue.dev documentation (continue.dev/docs), Claude Code release notes and help text, AutoGen/Microsoft research papers, CrewAI documentation, OpenHands/OpenDevin project README, LangGraph documentation. All accessed via training data current to August 2025.*
