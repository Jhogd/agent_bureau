# Visible Disagreement v1

Minimal orchestration loop for dual-agent responses with explicit disagreement labeling and follow-up adjudication.

## What it does
- Broadcasts one prompt to `agent_a` and `agent_b` in parallel.
- Normalizes each into a shared response schema.
- Classifies disagreement categories (`approach`, `fact`, `confidence_gap`).
- Appends each session to an append-only JSONL store.
- Supports follow-up actions: `choose_a`, `choose_b`, `reconcile`, `debate`.

## Run tests
```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```

## CLI usage
Stub mode (default):
```bash
PYTHONPATH=src python3 -m disagree_v1.cli "Design a job processing strategy"
```

With follow-up reconciliation:
```bash
PYTHONPATH=src python3 -m disagree_v1.cli "Design a job processing strategy" --action reconcile
```

With follow-up debate on disagreement index 0:
```bash
PYTHONPATH=src python3 -m disagree_v1.cli "Design a job processing strategy" --action debate --debate-index 0
```

Custom session store:
```bash
PYTHONPATH=src python3 -m disagree_v1.cli "Prompt" --store .disagree/sessions.jsonl
```

## Command mode (real agents)
Use `--mode command` and pass command templates for both agents.

```bash
PYTHONPATH=src python3 -m disagree_v1.cli "Your prompt" \
  --mode command \
  --agent-a-cmd 'claude-cli-command {prompt}' \
  --agent-b-cmd 'codex-cli-command {prompt}'
```

Rules:
- `command_template` is tokenized with shell-style parsing.
- If `{prompt}` token is present, it is replaced in-place.
- If `{prompt}` is absent, the prompt is appended as the final argument.
- Command output must be JSON with this schema:

```json
{
  "answer": "string",
  "proposed_actions": ["string"],
  "assumptions": ["string"],
  "confidence": 0.0
}
```

### Ready preset for your setup
Since your CLIs are launched as `claude` and `codex`, you can use the built-in preset:

```bash
PYTHONPATH=src python3 -m disagree_v1.cli "Your prompt" \
  --mode command \
  --preset claude-codex
```

This preset uses:
- Claude: non-interactive print mode with inline JSON schema.
- Codex: `codex exec` with `schemas/agent_response.schema.json`.

## Interactive launcher (what you asked for)
Start the program and answer prompts:

```bash
PYTHONPATH=src python3 -m disagree_v1.launch
```

It will:
- Detect installed agents (`claude`, `codex`) on your machine.
- Ask for Agent A and Agent B names.
- Ask for the exact command template to call each agent.
- Allow custom commands for other environments (e.g., `ssh`, `docker`, remote wrappers).
- Ask for your prompt and run both agents.
- Optionally run `reconcile` or `debate` follow-ups.
- Save your agent setup and reuse it on the next run.

### Saved config
- Default path: `.disagree/agents.json`
- Launcher asks for config path at startup (press Enter to use default).
- If saved agents exist, press Enter to reuse, or type `n` to reconfigure.

## Components
- `src/disagree_v1/orchestrator.py`: fan-out/fan-in orchestration.
- `src/disagree_v1/classifier.py`: disagreement labeling.
- `src/disagree_v1/adapters.py`: stub and external command adapters.
- `src/disagree_v1/adjudication.py`: reconcile/debate prompt builders and action executor.
- `src/disagree_v1/store.py`: append-only JSONL persistence.
- `src/disagree_v1/cli.py`: user-facing entrypoint.
