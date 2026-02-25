# Architecture

**Analysis Date:** 2026-02-21

## Pattern Overview

**Overall:** Fan-out/fan-in orchestration with append-only event logging and follow-up adjudication.

**Key Characteristics:**
- Parallel agent execution using ThreadPoolExecutor for concurrent request handling
- Structured response normalization into a unified schema
- Classification-based disagreement detection using deterministic heuristics
- Append-only JSONL persistence for immutable session history
- Optional follow-up actions (reconcile, debate) that re-invoke the orchestrator

## Layers

**Orchestration Layer:**
- Purpose: Coordinate parallel agent execution, collect responses, classify disagreements, persist sessions
- Location: `src/disagree_v1/orchestrator.py`
- Contains: `DisagreementOrchestrator` class
- Depends on: `AgentAdapter`, `classifier`, `SessionStore`
- Used by: CLI and launcher entry points

**Adapter Layer:**
- Purpose: Normalize diverse agent execution methods (stub, external command) into a common interface
- Location: `src/disagree_v1/adapters.py`
- Contains: `AgentAdapter` (Protocol), `StubAgentAdapter`, `CommandJsonAdapter`
- Depends on: `models.AgentResponse`, subprocess, JSON parsing
- Used by: Orchestrator

**Classification Layer:**
- Purpose: Analyze two agent responses and label disagreement categories
- Location: `src/disagree_v1/classifier.py`
- Contains: `classify_disagreements()` function with threshold-based heuristics
- Depends on: `models.AgentResponse`, `models.Disagreement`
- Used by: Orchestrator

**Persistence Layer:**
- Purpose: Append-only JSON Lines storage for immutable session audit trail
- Location: `src/disagree_v1/store.py`
- Contains: `JsonlSessionStore` class
- Depends on: pathlib, json
- Used by: Orchestrator

**Adjudication Layer:**
- Purpose: Build follow-up prompts for reconciliation or debate; execute follow-up actions
- Location: `src/disagree_v1/adjudication.py`
- Contains: `build_reconcile_prompt()`, `build_debate_prompt()`, `apply_action()`
- Depends on: `models.SessionResult`
- Used by: CLI, launcher

**Data Models Layer:**
- Purpose: Define immutable frozen dataclasses for type safety
- Location: `src/disagree_v1/models.py`
- Contains: `AgentResponse`, `Disagreement`, `SessionResult`
- Depends on: dataclasses
- Used by: All layers

**Preset Configuration:**
- Purpose: Generate command templates for known agent pairs
- Location: `src/disagree_v1/presets.py`
- Contains: `build_claude_codex_commands()` function
- Depends on: json
- Used by: CLI, launcher

**Entry Points:**
- CLI (batch): `src/disagree_v1/cli.py` - argument-driven orchestration
- Interactive launcher: `src/disagree_v1/launch.py` → `src/disagree_v1/launcher.py` - user-guided agent setup and execution

## Data Flow

**Initial Session (Core Flow):**

1. CLI/launcher collects prompt and agent configuration
2. Orchestrator receives two agent adapters and prompt
3. Orchestrator executes both agents in parallel using ThreadPoolExecutor
4. Each adapter normalizes agent output into `AgentResponse` schema
5. Orchestrator passes both responses to classifier
6. Classifier produces list of `Disagreement` objects (approach, fact, confidence_gap)
7. Orchestrator wraps all data in `SessionResult`
8. SessionResult is serialized to dict and appended to JSONL store (idempotent append)
9. SessionResult is returned to caller for display

**Follow-Up Action Flow (Adjudication):**

1. User selects follow-up action: none, choose_a, choose_b, reconcile, or debate
2. If reconcile: `build_reconcile_prompt()` constructs a meta-prompt combining both answers + disagreement summary
3. If debate: `build_debate_prompt()` constructs a meta-prompt focusing on one disagreement index
4. `apply_action()` re-invokes orchestrator with new prompt
5. Orchestrator re-runs both agents on the follow-up prompt
6. Result persists as a separate session in JSONL store

**State Management:**
- Immutable session state via frozen dataclasses (`SessionResult`, `AgentResponse`)
- Append-only persistence (no updates or deletes)
- Each session is independent (no cross-session state)
- ThreadPoolExecutor manages parallel execution state internally

## Key Abstractions

**AgentAdapter Protocol:**
- Purpose: Define the interface for agent execution (duck typing)
- Examples: `StubAgentAdapter`, `CommandJsonAdapter` in `src/disagree_v1/adapters.py`
- Pattern: Protocol-based polymorphism allows any object with a `run(prompt: str) -> AgentResponse` method

**AgentResponse Dataclass:**
- Purpose: Standardized schema for all agent outputs
- Defined in: `src/disagree_v1/models.py`
- Fields: answer (str), proposed_actions (list[str]), assumptions (list[str]), confidence (float [0, 1])
- Frozen: Immutable after creation, hashable for use in sets

**Disagreement Classification:**
- Purpose: Categorize differences between two responses using heuristics
- Logic: `src/disagree_v1/classifier.py`
- Categories:
  - `approach`: Different proposed_actions sets (after normalization)
  - `fact`: Different assumptions (symmetric difference of assumption sets)
  - `confidence_gap`: Confidence difference >= 0.30 threshold
- Output: List of `Disagreement` objects with kind and summary

**CommandJsonAdapter JSON Extraction:**
- Purpose: Robustly extract JSON from command output that may contain surrounding text
- Logic: `src/disagree_v1/adapters.py` lines 75-94
- Strategy: First attempt full parse; if fails, locate { and } boundaries and extract substring
- Validates extracted payload has required keys and correct types

## Entry Points

**CLI Entry Point:**
- Location: `src/disagree_v1/cli.py`
- Invocation: `PYTHONPATH=src python3 -m disagree_v1.cli "prompt" [options]`
- Responsibilities:
  - Parse command-line arguments (prompt, store path, mode, preset, agent commands, action)
  - Instantiate appropriate adapters (stub or command-based)
  - Create orchestrator and session store
  - Run initial session
  - Apply optional follow-up action
  - Pretty-print results
- Modes: stub (deterministic for testing) or command (external executables)

**Interactive Launcher Entry Point:**
- Location: `src/disagree_v1/launch.py` (thin wrapper)
- Implementation: `src/disagree_v1/launcher.py`
- Invocation: `PYTHONPATH=src python3 -m disagree_v1.launch`
- Responsibilities:
  - Detect installed agents on PATH (claude, codex)
  - Load or prompt for agent configuration
  - Build adapter instances from user input
  - Execute orchestrator with user prompt
  - Apply optional follow-up action
  - Save agent config for future reuse

## Error Handling

**Strategy:** Fail-fast with informative error messages. No silent degradation.

**Patterns:**
- `CommandJsonAdapter._parse_payload()`: Returns ValueError if JSON cannot be extracted, with agent name for debugging
- `CommandJsonAdapter._validate_payload()`: Type checks all fields; raises ValueError if schema violated
- `apply_action()`: Raises ValueError for invalid action or debate index out of bounds
- `launcher.run_interactive()`: Catches orchestrator ValueError, prints tip, returns gracefully
- `subprocess.run()`: 90-second timeout; TimeoutExpired raises ValueError with command prefix

## Cross-Cutting Concerns

**Logging:** No persistent logging framework. Output via print() for CLI, write to JSONL for sessions.

**Validation:**
- Agent adapters validate output schema before returning
- `CommandJsonAdapter` checks required keys and types
- `SessionResult.to_dict()` assumes valid models (relies on type system)

**Authentication:**
- None built-in. Command adapters can embed auth (e.g., `ssh`, API keys in command templates)
- Agent config files (`.disagree/agents.json`) contain command templates only, not secrets

**Concurrency:**
- ThreadPoolExecutor with max_workers=2 for fan-out agent execution
- No locking or semaphores; each session is independent
- JSONL append uses file I/O atomicity (one line per session)
