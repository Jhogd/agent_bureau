from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

from disagree_v1.adapters import CommandJsonAdapter
from disagree_v1.adjudication import apply_action
from disagree_v1.orchestrator import DisagreementOrchestrator
from disagree_v1.presets import build_claude_codex_commands
from disagree_v1.store import JsonlSessionStore


def default_config_path() -> Path:
    return Path(".disagree/agents.json")


def load_agent_config(path: Path) -> dict[str, dict[str, str]] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "agent_a" not in payload or "agent_b" not in payload:
        return None
    return payload


def save_agent_config(path: Path, agent_a: dict[str, str], agent_b: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"agent_a": agent_a, "agent_b": agent_b}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def detect_available_agents(which_fn: Callable[[str], str | None] = shutil.which) -> list[dict[str, str]]:
    supported = ["claude", "codex"]
    detected: list[dict[str, str]] = []
    for name in supported:
        path = which_fn(name)
        if path:
            detected.append({"name": name, "path": path})
    return detected


def choose_default_command(agent_name: str, schema_path: str) -> str:
    claude_cmd, codex_cmd = build_claude_codex_commands(schema_path)
    if agent_name == "claude":
        return claude_cmd
    if agent_name == "codex":
        return codex_cmd
    return ""


def normalize_command_template(command: str, agent_name: str, schema_path: str) -> str:
    raw = command.strip()
    default = choose_default_command(agent_name, schema_path)
    if default and raw == agent_name:
        return default
    return raw


def collect_two_agents(
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
    detected: list[dict[str, str]] | None = None,
    schema_path: str = "schemas/agent_response.schema.json",
    saved: dict[str, dict[str, str]] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    detected = detected or detect_available_agents()
    names = [item["name"] for item in detected]

    if names:
        print_fn("Detected installed agents: " + ", ".join(names))
    else:
        print_fn("No known agents auto-detected. You can still enter custom command templates.")

    if saved:
        print_fn(
            "Saved agents found: "
            f"A={saved['agent_a']['name']}, B={saved['agent_b']['name']}"
        )
        reuse = input_fn("Press Enter to reuse saved agents, or type 'n' to reconfigure: ").strip().lower()
        if reuse != "n":
            return saved["agent_a"], saved["agent_b"]

    def _collect(label: str) -> dict[str, str]:
        name = input_fn(f"{label} name (e.g. claude, codex, remote_claude): ").strip()
        while not name:
            name = input_fn(f"{label} name is required: ").strip()

        default = choose_default_command(name, schema_path)
        if default:
            print_fn(f"Suggested command for {name}: {default}")
            command = input_fn(
                f"{label} command template (press Enter to use suggested; include {{prompt}}): "
            ).strip()
            if not command:
                command = default
        else:
            command = input_fn(
                f"{label} command template (include {{prompt}}; can be ssh/docker/local): "
            ).strip()

        while not command:
            command = input_fn(f"{label} command template is required: ").strip()

        normalized = normalize_command_template(command, name, schema_path)
        if normalized != command:
            print_fn(f"Using suggested non-interactive command for {name}.")
            command = normalized

        return {"name": name, "command": command}

    return _collect("Agent A"), _collect("Agent B")


def _print_result(result, title: str = "Result") -> None:
    print(f"\n{title}")
    print("Prompt:", result.prompt)
    print("\nAgent A:")
    print(result.agent_a.answer)
    print("\nAgent B:")
    print(result.agent_b.answer)
    print("\nDisagreements:")
    if not result.disagreements:
        print("- none")
    for idx, item in enumerate(result.disagreements):
        print(f"- ({idx}) [{item.kind}] {item.summary}")


def run_interactive() -> None:
    print("Visible Disagreement Launcher")

    config_path_input = input("Agent config path [.disagree/agents.json]: ").strip()
    config_path = Path(config_path_input) if config_path_input else default_config_path()
    saved = load_agent_config(config_path)

    agent_a, agent_b = collect_two_agents(saved=saved)
    if not saved or saved.get("agent_a") != agent_a or saved.get("agent_b") != agent_b:
        save_agent_config(config_path, agent_a, agent_b)
        print(f"Saved agent config to {config_path}")

    prompt = input("Prompt to send both agents: ").strip()
    while not prompt:
        prompt = input("Prompt is required: ").strip()

    store_path = input("Session store path [.disagree/sessions.jsonl]: ").strip() or ".disagree/sessions.jsonl"

    action = input("Follow-up action [none/choose_a/choose_b/reconcile/debate] (default none): ").strip() or "none"
    debate_index = 0
    if action == "debate":
        raw_index = input("Disagreement index for debate [0]: ").strip()
        debate_index = int(raw_index) if raw_index else 0

    store = JsonlSessionStore(Path(store_path))
    orchestrator = DisagreementOrchestrator(
        CommandJsonAdapter(agent_a["name"], agent_a["command"]),
        CommandJsonAdapter(agent_b["name"], agent_b["command"]),
        store,
    )

    try:
        result = orchestrator.run(prompt)
    except ValueError as exc:
        print(f"\nRun failed: {exc}")
        print("Tip: use non-interactive JSON commands, not bare 'claude' or 'codex'.")
        print("Re-run launcher and press Enter at command prompts to accept suggested commands.")
        return
    _print_result(result, "Initial Result")

    follow_up = apply_action(action, orchestrator, result, debate_index)
    if follow_up is not None:
        _print_result(follow_up, "Follow-Up Result")
