# External Integrations

**Analysis Date:** 2026-02-21

## APIs & External Services

**Agent CLIs:**
- Claude CLI - External agent responding to prompts
  - Integration: `disagree_v1.adapters.CommandJsonAdapter`
  - Called via subprocess with command template
  - Expected output: JSON with schema `schemas/agent_response.schema.json`

- Codex CLI - External agent responding to prompts
  - Integration: `disagree_v1.adapters.CommandJsonAdapter`
  - Called via subprocess with command template
  - Expected output: JSON with schema `schemas/agent_response.schema.json`

**Command Execution:**
- External CLI commands via subprocess
  - Location: `src/disagree_v1/adapters.py` - `CommandJsonAdapter` class
  - Timeout: 90 seconds per command execution
  - Error handling: TimeoutExpired raises ValueError with command details

## Data Storage

**Databases:**
- Not used - No database integration

**File Storage:**
- Local filesystem only - Append-only JSONL files
  - Location: `src/disagree_v1/store.py` - `JsonlSessionStore` class
  - Default path: `.disagree/sessions.jsonl`
  - Format: One JSON object per line (newline-delimited JSON)
  - Purpose: Persistent storage of session results, agent responses, and disagreement classifications

**Agent Configuration Storage:**
- Local filesystem - JSON configuration files
  - Location: `.disagree/agents.json` (default)
  - Format: Plain JSON
  - Content: Agent names and command templates for reproducible runs
  - Created by: `src/disagree_v1/launcher.py` - `save_agent_config()` function

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None - System is auth-agnostic
- External CLI tools (Claude, Codex) handle their own authentication
- No credentials managed by this application

## Monitoring & Observability

**Error Tracking:**
- Not integrated - Basic exception handling in adapters

**Logs:**
- Console output only (stdout/stderr)
- No persistent logging framework
- Error details printed to console during CLI runs

## CI/CD & Deployment

**Hosting:**
- Not applicable - Command-line tool for local execution
- Designed to run locally with external agent CLIs

**CI Pipeline:**
- Not detected
- Test execution: `python3 -m unittest discover -s tests -p 'test_*.py'` or `pytest`

## Environment Configuration

**Required environment variables:**
- None - Application is configured via:
  - Command-line arguments (via `argparse`)
  - Interactive prompts (via `input()`)
  - File paths (JSON config and session store)

**Secrets location:**
- None - No secrets managed by this application
- External CLI tools handle their own credential management

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Command-Line Interface

**Agent Command Templates:**
- Location: `src/disagree_v1/presets.py` - `build_claude_codex_commands()`
- Template variables: `{prompt}` placeholder for prompt injection
- Template parsing: Shell-style tokenization via `shlex.split()`
- Behavior: If `{prompt}` present, replaces in-place; otherwise appends as final argument

**Preset Commands:**
- Claude preset: `claude -p --output-format json --json-schema '[schema]' {prompt}`
  - Flags: `-p` (non-interactive), `--output-format json` (JSON output), `--json-schema` (schema validation)

- Codex preset: `codex exec --skip-git-repo-check --output-schema schemas/agent_response.schema.json {prompt}`
  - Flags: `--skip-git-repo-check`, `--output-schema` (external schema file reference)

**Agent Detection:**
- Location: `src/disagree_v1/launcher.py` - `detect_available_agents()`
- Method: Uses `shutil.which()` to check if `claude` and `codex` are available on system PATH
- Supported agents: ["claude", "codex"]

## JSON Response Contract

**Schema Location:**
- `schemas/agent_response.schema.json` - Canonical schema

**Validation Points:**
- `src/disagree_v1/adapters.py` - `CommandJsonAdapter._validate_payload()`
  - Validates structure and types
  - Required fields: answer, proposed_actions, assumptions, confidence
  - Confidence range: 0.0 to 1.0 (validated as float)

**Payload Structure:**
```json
{
  "answer": "string",
  "proposed_actions": ["string"],
  "assumptions": ["string"],
  "confidence": 0.0
}
```

---

*Integration audit: 2026-02-21*
