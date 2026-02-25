from __future__ import annotations

import argparse
from pathlib import Path

from disagree_v1.adapters import CommandJsonAdapter, StubAgentAdapter
from disagree_v1.adjudication import apply_action
from disagree_v1.orchestrator import DisagreementOrchestrator
from disagree_v1.presets import build_claude_codex_commands
from disagree_v1.store import JsonlSessionStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Visible disagreement CLI v1")
    parser.add_argument("prompt", help="Prompt to broadcast to both agents")
    parser.add_argument(
        "--store",
        default=".disagree/sessions.jsonl",
        help="Path to append-only JSONL session log",
    )
    parser.add_argument(
        "--mode",
        choices=["stub", "command"],
        default="stub",
        help="Agent mode: deterministic stub or external command adapters",
    )
    parser.add_argument(
        "--preset",
        choices=["none", "claude-codex"],
        default="none",
        help="Prebuilt command templates for known agent pairs",
    )
    parser.add_argument("--agent-a-cmd", default="", help="Command template for agent A")
    parser.add_argument("--agent-b-cmd", default="", help="Command template for agent B")
    parser.add_argument(
        "--action",
        choices=["none", "choose_a", "choose_b", "reconcile", "debate"],
        default="none",
        help="Optional follow-up adjudication action",
    )
    parser.add_argument(
        "--debate-index",
        type=int,
        default=0,
        help="Disagreement index for debate action",
    )
    return parser


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


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    store = JsonlSessionStore(Path(args.store))
    if args.mode == "command":
        agent_a_cmd = args.agent_a_cmd
        agent_b_cmd = args.agent_b_cmd
        if args.preset == "claude-codex":
            preset_a, preset_b = build_claude_codex_commands("schemas/agent_response.schema.json")
            if not agent_a_cmd:
                agent_a_cmd = preset_a
            if not agent_b_cmd:
                agent_b_cmd = preset_b
        if not agent_a_cmd or not agent_b_cmd:
            raise SystemExit(
                "--agent-a-cmd and --agent-b-cmd are required in command mode, "
                "or set --preset claude-codex"
            )
        agent_a = CommandJsonAdapter("agent_a", agent_a_cmd)
        agent_b = CommandJsonAdapter("agent_b", agent_b_cmd)
    else:
        agent_a = StubAgentAdapter("architecture")
        agent_b = StubAgentAdapter("delivery")

    orchestrator = DisagreementOrchestrator(agent_a, agent_b, store)
    result = orchestrator.run(args.prompt)
    _print_result(result, "Initial Result")

    print("\nAdjudication options:")
    print("1. choose_a")
    print("2. choose_b")
    print("3. reconcile")
    print("4. debate")

    follow_up = apply_action(args.action, orchestrator, result, args.debate_index)
    if follow_up is not None:
        _print_result(follow_up, "Follow-Up Result")


if __name__ == "__main__":
    main()
