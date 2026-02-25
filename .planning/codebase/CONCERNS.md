# Codebase Concerns

**Analysis Date:** 2026-02-21

## Tech Debt

**Launcher module complexity and input validation:**
- Issue: `src/disagree_v1/launcher.py` (172 lines) handles interactive UI, agent detection, config persistence, and command template normalization in a single module. This violates SRP and makes the module difficult to test comprehensively.
- Files: `src/disagree_v1/launcher.py`
- Impact: Changes to input handling, config storage, or agent detection require careful coordination to avoid breaking the interactive flow. Testing edge cases requires mocking multiple concerns (file I/O, user input, agent detection).
- Fix approach: Extract three separate concerns: (1) `AgentConfigPersistence` (save/load), (2) `AgentDetector` (command availability detection), (3) `InteractiveCollector` (user prompts and flow). This will also improve testability and allow reuse of these pieces independently.

**CommandJsonAdapter JSON extraction is brittle:**
- Issue: `src/disagree_v1/adapters.py:75-94` uses substring searching to extract JSON from wrapped output. This approach finds the first `{` and last `}` in the output, which fails if the agent's answer text contains unbalanced braces or JSON-like structures.
- Files: `src/disagree_v1/adapters.py` (lines 75-94)
- Impact: Agents that output JSON in their answer field or explanations with code blocks containing JSON will produce parsing errors. The test at line 155-162 only covers the specific case of markdown-wrapped JSON.
- Fix approach: Use a proper JSON streaming parser or require agents to output pure JSON (use `json.decoder.JSONDecoder` with configurable error handlers). Alternatively, add a validation flag to require agents output exactly one complete JSON object at the root level, rejecting mixed content.

**Confidence value validation lacks range enforcement:**
- Issue: `src/disagree_v1/models.py:11` and `src/disagree_v1/presets.py:13` define confidence as a number but tests pass values 0.0-1.0 without explicit bounds checking. `src/disagree_v1/adapters.py:113-116` coerces confidence to float but doesn't validate the 0-1 range.
- Files: `src/disagree_v1/models.py`, `src/disagree_v1/adapters.py:114`
- Impact: Agents could return confidence values < 0 or > 1, violating the schema contract and potentially breaking threshold logic in `src/disagree_v1/classifier.py:33-34`.
- Fix approach: Add explicit range validation in `CommandJsonAdapter._validate_payload()` after line 114: `if not (0.0 <= confidence_value <= 1.0): raise ValueError(...)`.

**Store creates parent directories silently:**
- Issue: `src/disagree_v1/store.py:10` calls `self._path.parent.mkdir(parents=True, exist_ok=True)` without logging or control. If the filesystem path doesn't exist or lacks permissions, sessions could be lost silently or fail at runtime.
- Files: `src/disagree_v1/store.py:10`
- Impact: No user feedback if session store cannot be created. In distributed/remote setups, permission issues may not surface until after the orchestrator completes its work.
- Fix approach: Replace silent mkdir with explicit check and error: `if not self._path.parent.is_dir(): raise ValueError(f"Session store directory cannot be created: {self._path.parent}")`.

**Debate and reconcile prompts have no length limits:**
- Issue: `src/disagree_v1/adjudication.py:6-30` builds reconcile and debate prompts by concatenating full agent responses, disagreement summaries, and original prompt. Very long answers or prompts could exceed API context limits.
- Files: `src/disagree_v1/adjudication.py:6-30`
- Impact: Follow-up actions (reconcile/debate) may fail silently if the combined prompt exceeds the agent's context window. No truncation or warning is provided.
- Fix approach: Add maximum prompt length constant and truncate agent answers with ellipsis. Log a warning if truncation occurs.

## Known Bugs

**Integer debate index not validated before negative indexing:**
- Symptoms: `apply_action("debate", orchestrator, session, -1)` will successfully access the last disagreement due to Python's negative indexing, violating the API contract.
- Files: `src/disagree_v1/adjudication.py:18-20`
- Trigger: Pass a negative integer to `debate_index` parameter in `apply_action()` or command line `--debate-index -1`.
- Workaround: Check index bounds in calling code before invoking `apply_action()`. Currently only `launcher.py:151` and `cli.py:99` call this, and both trust user input.
- Fix: Change line 19 from `if disagreement_index < 0` to `if disagreement_index < 0 or disagreement_index >= len(session.disagreements)` to catch both bounds.

**Subprocess timeout error message is truncated:**
- Symptoms: When a command times out, `src/disagree_v1/adapters.py:50-51` builds an error message showing only the first 3 tokens of the command, making debugging difficult for long commands.
- Files: `src/disagree_v1/adapters.py:50-51`
- Trigger: Run any agent command that exceeds the 90-second timeout.
- Workaround: Add debug logging to capture the full command before execution.
- Fix: Store the full command and include it in the timeout error: `raise ValueError(f"Command timed out (90s): {self.command_template}") from exc`.

## Security Considerations

**Command template injection via prompt parameter:**
- Risk: `src/disagree_v1/adapters.py:63-68` uses `shlex.split()` to parse command templates but performs direct string substitution with the prompt. If `{prompt}` token is present, the prompt is inserted verbatim. An attacker-controlled prompt containing shell metacharacters could break out of the substitution context if the shell is invoked without proper quoting.
- Files: `src/disagree_v1/adapters.py:63-68`, `src/disagree_v1/launcher.py:100`
- Current mitigation: `subprocess.run()` is called with `args` list (line 48), which avoids shell interpretation. However, the user is responsible for constructing safe command templates in `launcher.py:100-104`.
- Recommendations: (1) Document that command templates are not shell-safe and should not be used with untrusted prompts. (2) Add a `--safe-mode` flag that escapes prompt before substitution using `shlex.quote()`. (3) Validate command templates don't use shell operators like `|`, `>`, `;`.

**Session store appends without atomic writes:**
- Risk: `src/disagree_v1/store.py:13-14` opens the file in append mode and writes without locks. Concurrent writes from multiple orchestrator instances could interleave or corrupt the JSONL log.
- Files: `src/disagree_v1/store.py:12-14`
- Current mitigation: JSONL format tolerates partial lines, and append-only semantics mean earlier records are safe. However, the most recent record could be corrupted or incomplete.
- Recommendations: (1) Add file locking using `fcntl.flock()` (Unix) or `msvcrt.locking()` (Windows). (2) Write to a temporary file and atomically rename, using `.tmp` extension. (3) Document that concurrent writes are not supported and suggest a queue-based store for multi-instance deployments.

**Agent response contents are not sanitized:**
- Risk: Agent responses (answer, proposed_actions, assumptions) are printed to stdout and persisted as JSON without validation. If an agent is compromised or returns malicious content, it could execute unintended operations.
- Files: `src/disagree_v1/launcher.py:116-127`, `src/disagree_v1/cli.py:50-61`, `src/disagree_v1/store.py:12-14`
- Current mitigation: Content is treated as text only; no evaluation or execution happens. Persistence is plain JSON without code execution risk.
- Recommendations: (1) Add length limits to answer and assumption fields to prevent DoS via huge responses. (2) Sanitize string content before printing (e.g., replace control characters). (3) Document assumptions about agent trustworthiness.

## Performance Bottlenecks

**Disagreement classification is O(n²) set operations:**
- Problem: `src/disagree_v1/classifier.py:16,24` normalize and compare proposed_actions and assumptions using set symmetric difference. For large lists (100+ items), this becomes slow.
- Files: `src/disagree_v1/classifier.py:9-10,16,24`
- Cause: `_normalize()` is called twice per classification (once for actions, once for assumptions), and the symmetric difference operation creates temporary sets. No caching.
- Improvement path: Cache normalization results or pass pre-normalized sets to avoid redundant lowercasing and stripping.

**CLI repetitively loads schema for preset commands:**
- Problem: `src/disagree_v1/cli.py:73` and `src/disagree_v1/launcher.py:45` both call `build_claude_codex_commands()`, which rebuilds the JSON schema string every time, even though it's identical.
- Files: `src/disagree_v1/presets.py:6-18`, `src/disagree_v1/cli.py:73`, `src/disagree_v1/launcher.py:45`
- Cause: Schema is regenerated on each call; no module-level constant.
- Improvement path: Define `_AGENT_RESPONSE_SCHEMA` as a module constant in `presets.py` and reuse it.

## Fragile Areas

**Launcher interactive flow has no timeout on user input:**
- Files: `src/disagree_v1/launcher.py:133,142,146,148,151`
- Why fragile: `input()` calls block indefinitely. If a user walks away or a terminal is left open, the process hangs. No readline history or cancellation is exposed.
- Safe modification: Wrap `input()` calls with timeout using `signal.alarm()` (Unix) or `threading.Timer()` (cross-platform). Catch timeout and exit gracefully.
- Test coverage: No tests for timeout behavior or signal handling.

**CommandJsonAdapter assumes synchronous subprocess behavior:**
- Files: `src/disagree_v1/adapters.py:47-52`
- Why fragile: If an agent spawns child processes that outlive the parent, `subprocess.run(timeout=90)` may not terminate them correctly. The orchestrator could leak zombie processes.
- Safe modification: Use `subprocess.run(..., preexec_fn=os.setsid, ...)` (Unix) and `subprocess.run(..., creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, ...)` (Windows) to create process groups, allowing cleanup of descendants on timeout.
- Test coverage: No tests for process cleanup or long-running subprocesses.

**Session data model has no versioning:**
- Files: `src/disagree_v1/models.py:20-33`, `src/disagree_v1/store.py:12-14`
- Why fragile: If the schema of `SessionResult` changes (e.g., new fields added), old persisted records in the JSONL store become incompatible. No migration path exists.
- Safe modification: Add a `schema_version` field to SessionResult and implement a version-aware loader in `JsonlSessionStore`. Document breaking changes.
- Test coverage: No tests for forward/backward compatibility.

## Scaling Limits

**Orchestrator runs agents serially in thread pool with fixed pool size:**
- Current capacity: 2 concurrent agents via ThreadPoolExecutor (line 23 of `orchestrator.py`)
- Limit: If agents take 30+ seconds each, total latency is 30+ seconds. No parallelism beyond the two agents.
- Scaling path: Use async/await with `asyncio` instead of ThreadPoolExecutor for true concurrent execution and better resource utilization. Consider supporting 3+ agents.

**JSONL session store has unbounded file growth:**
- Current capacity: All sessions appended to a single file indefinitely.
- Limit: Very large JSONL files (millions of records) become slow to read for reporting or analysis.
- Scaling path: Implement log rotation by date/size. Provide a tool to archive old sessions or migrate to a database.

## Dependencies at Risk

**No explicit dependencies declared in pyproject.toml:**
- Risk: `pyproject.toml:10` specifies `dependencies = []`. Code imports `json`, `subprocess`, `pathlib` (all stdlib) but the project lacks explicit dependency management. If future features require third-party packages (e.g., for async or database storage), there's no central record.
- Impact: Unclear what versions of stdlib are required (e.g., `json` is available in all Python versions, but `asyncio` requires careful version management).
- Migration plan: Add a `[project.optional-dependencies]` section for future async/database dependencies. Document minimum Python version (currently 3.10 per pyproject.toml:9).

**Subprocess timeout uses hardcoded 90 seconds:**
- Risk: `src/disagree_v1/adapters.py:48` hardcodes `timeout=90`. This is not configurable and may be too short for slow agents or too long for fast-fail scenarios.
- Impact: Users cannot adjust timeout without modifying code.
- Migration plan: Make timeout configurable via environment variable or constructor parameter. Document the tradeoff between latency and agent reliability.

## Missing Critical Features

**No logging or observability:**
- Problem: The orchestrator has no logging. Errors in adapters or store are raised silently or printed to stderr. No structured logging for debugging production issues.
- Blocks: Cannot troubleshoot why an orchestrator run failed or how long agents took.
- Fix approach: Add `logging` module usage. Log adapter start/end, store writes, disagreement classifications. Expose log level via CLI flag or environment variable.

**No validation of disagreement index in reconcile vs debate:**
- Problem: `adjudication.py:37` calls `orchestrator.run(build_reconcile_prompt(...))` but does not pass `debate_index`. If a user calls reconcile followed by debate with a stale index, results are unpredictable.
- Blocks: Multi-step follow-ups are error-prone.
- Fix approach: Store session ID and validate that all follow-up actions operate on the same session. Alternatively, reject debate if the session has already been modified by reconcile.

**No agent response caching:**
- Problem: If the same prompt is sent twice, both agents are run again. No memoization.
- Blocks: Experimentation with the same prompt requires re-running potentially slow agents.
- Fix approach: Add optional caching layer that keys on prompt and returns cached agent responses if available. Provide `--no-cache` flag to force fresh runs.

## Test Coverage Gaps

**CommandJsonAdapter._parse_payload() has untested edge cases:**
- What's not tested: Payloads with extra fields beyond the required schema, nested JSON structures, very large JSON objects, JSON with unicode or special characters.
- Files: `src/disagree_v1/adapters.py:75-94`, `test_v1_flow.py:126-162`
- Risk: Unexpected agent output shapes could cause silent data loss or type errors.
- Priority: Medium

**Disagreement classification thresholds are not validated:**
- What's not tested: Confidence values exactly at the threshold (0.30), edge cases where proposed_actions differ by one item, very long assumption lists.
- Files: `src/disagree_v1/classifier.py`, `test_v1_flow.py:43-62`
- Risk: Boundary condition bugs in disagreement detection could go unnoticed.
- Priority: Medium

**Store file permissions and directory creation failures:**
- What's not tested: Directory creation fails due to permissions, file already exists as a directory, disk full, filesystem is read-only.
- Files: `src/disagree_v1/store.py`, `test_v1_flow.py:101-124`
- Risk: Sessions silently fail to persist in edge cases.
- Priority: High

**Launcher agent config persistence race conditions:**
- What's not tested: Concurrent calls to `save_agent_config()`, config file corruption mid-write, config file deleted between load and save.
- Files: `src/disagree_v1/launcher.py:28-31`, `test_v1_flow.py:280-291`
- Risk: Config could be lost or corrupted in concurrent scenarios.
- Priority: Medium

**Orchestrator error propagation from adapters:**
- What's not tested: What happens if an adapter raises an exception during orchestrator.run(). Does it propagate, or is it caught?
- Files: `src/disagree_v1/orchestrator.py:22-37`
- Risk: Adapter errors could crash the orchestrator or leave sessions in inconsistent state.
- Priority: High

---

*Concerns audit: 2026-02-21*
