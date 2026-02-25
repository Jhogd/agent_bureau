import json
import tempfile
import unittest
from pathlib import Path

from disagree_v1.adapters import CommandJsonAdapter
from disagree_v1.adjudication import apply_action, build_debate_prompt, build_reconcile_prompt
from disagree_v1.classifier import classify_disagreements
from disagree_v1.launcher import (
    choose_default_command,
    collect_two_agents,
    detect_available_agents,
    load_agent_config,
    normalize_command_template,
    save_agent_config,
)
from disagree_v1.models import AgentResponse
from disagree_v1.orchestrator import DisagreementOrchestrator
from disagree_v1.presets import build_claude_codex_commands
from disagree_v1.store import JsonlSessionStore


class FakeAdapter:
    def __init__(self, name: str, response: AgentResponse):
        self.name = name
        self._response = response

    def run(self, prompt: str) -> AgentResponse:
        return self._response


class TrackingOrchestrator:
    def __init__(self, result):
        self.calls: list[str] = []
        self._result = result

    def run(self, prompt: str):
        self.calls.append(prompt)
        return self._result


class V1FlowTests(unittest.TestCase):
    def test_classifier_labels_approach_and_confidence_gap(self) -> None:
        a = AgentResponse(
            answer="Use a queue-based worker model.",
            proposed_actions=["Introduce message queue", "Add retry policy"],
            assumptions=["Background jobs are acceptable"],
            confidence=0.9,
        )
        b = AgentResponse(
            answer="Use direct synchronous calls.",
            proposed_actions=["Keep synchronous API", "Return detailed errors"],
            assumptions=["Latency must stay under 50ms"],
            confidence=0.3,
        )

        disagreements = classify_disagreements(a, b)
        kinds = {d.kind for d in disagreements}

        self.assertIn("approach", kinds)
        self.assertIn("fact", kinds)
        self.assertIn("confidence_gap", kinds)

    def test_orchestrator_runs_and_persists_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = JsonlSessionStore(tmp_path / "sessions.jsonl")
            adapter_a = FakeAdapter(
                "agent_a",
                AgentResponse(
                    answer="Prefer event queue.",
                    proposed_actions=["Add queue"],
                    assumptions=["Can add infra"],
                    confidence=0.8,
                ),
            )
            adapter_b = FakeAdapter(
                "agent_b",
                AgentResponse(
                    answer="Keep simple in-process design.",
                    proposed_actions=["Keep in process"],
                    assumptions=["Single node deployment"],
                    confidence=0.6,
                ),
            )

            orchestrator = DisagreementOrchestrator(adapter_a, adapter_b, store)
            result = orchestrator.run("How should we process jobs?")

            self.assertEqual(result.prompt, "How should we process jobs?")
            self.assertEqual(result.agent_a.answer, "Prefer event queue.")
            self.assertEqual(result.agent_b.answer, "Keep simple in-process design.")
            self.assertGreaterEqual(len(result.disagreements), 1)

            lines = (tmp_path / "sessions.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            persisted = json.loads(lines[0])
            self.assertEqual(persisted["prompt"], "How should we process jobs?")
            self.assertEqual(persisted["agent_a"]["answer"], "Prefer event queue.")

    def test_store_appends_multiple_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = JsonlSessionStore(tmp_path / "sessions.jsonl")
            first = {
                "prompt": "one",
                "agent_a": {},
                "agent_b": {},
                "disagreements": [],
            }
            second = {
                "prompt": "two",
                "agent_a": {},
                "agent_b": {},
                "disagreements": [],
            }

            store.append(first)
            store.append(second)

            lines = (tmp_path / "sessions.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["prompt"], "one")
            self.assertEqual(json.loads(lines[1])["prompt"], "two")

    def test_command_json_adapter_parses_structured_output(self) -> None:
        def fake_runner(args: list[str]) -> str:
            self.assertEqual(args[0], "fake-agent")
            self.assertIn("Solve safely", args)
            return json.dumps(
                {
                    "answer": "Use queue workers.",
                    "proposed_actions": ["Add queue", "Add retries"],
                    "assumptions": ["Infra available"],
                    "confidence": 0.81,
                }
            )

        adapter = CommandJsonAdapter("agent_a", "fake-agent {prompt}", fake_runner)
        result = adapter.run("Solve safely")

        self.assertEqual(result.answer, "Use queue workers.")
        self.assertEqual(result.proposed_actions, ["Add queue", "Add retries"])
        self.assertEqual(result.assumptions, ["Infra available"])
        self.assertEqual(result.confidence, 0.81)

    def test_command_json_adapter_rejects_invalid_output(self) -> None:
        def fake_runner(_: list[str]) -> str:
            return "not-json"

        adapter = CommandJsonAdapter("agent_b", "fake-agent {prompt}", fake_runner)
        with self.assertRaises(ValueError):
            adapter.run("anything")

    def test_command_json_adapter_extracts_json_from_text_wrapper(self) -> None:
        def fake_runner(_: list[str]) -> str:
            return 'Result:\\n```json\\n{"answer":"A","proposed_actions":["x"],"assumptions":["y"],"confidence":0.7}\\n```'

        adapter = CommandJsonAdapter("agent_b", "fake-agent {prompt}", fake_runner)
        result = adapter.run("anything")
        self.assertEqual(result.answer, "A")
        self.assertEqual(result.confidence, 0.7)

    def test_build_reconcile_and_debate_prompts(self) -> None:
        a = AgentResponse(
            answer="Use queue",
            proposed_actions=["Add queue"],
            assumptions=["Background workers allowed"],
            confidence=0.9,
        )
        b = AgentResponse(
            answer="Keep synchronous",
            proposed_actions=["Keep sync"],
            assumptions=["No new infra"],
            confidence=0.5,
        )
        store = JsonlSessionStore(Path(tempfile.gettempdir()) / "noop.jsonl")
        session = DisagreementOrchestrator(FakeAdapter("a", a), FakeAdapter("b", b), store).run("How?")

        reconcile_prompt = build_reconcile_prompt(session)
        debate_prompt = build_debate_prompt(session, 0)
        self.assertIn("Reconcile", reconcile_prompt)
        self.assertIn("Debate this disagreement", debate_prompt)

    def test_apply_action_runs_follow_up_prompt(self) -> None:
        session = type(
            "Session",
            (),
            {
                "prompt": "base prompt",
                "agent_a": AgentResponse("A", ["a1"], ["ax"], 0.8),
                "agent_b": AgentResponse("B", ["b1"], ["bx"], 0.6),
                "disagreements": [type("D", (), {"kind": "approach", "summary": "Different plans"})()],
            },
        )()
        orchestrator = TrackingOrchestrator("next-result")

        choose = apply_action("choose_a", orchestrator, session)
        self.assertIsNone(choose)

        reconcile = apply_action("reconcile", orchestrator, session)
        debate = apply_action("debate", orchestrator, session, 0)
        self.assertEqual(reconcile, "next-result")
        self.assertEqual(debate, "next-result")
        self.assertEqual(len(orchestrator.calls), 2)

    def test_build_claude_codex_preset_commands(self) -> None:
        claude_cmd, codex_cmd = build_claude_codex_commands("schemas/agent_response.schema.json")
        self.assertIn("claude -p", claude_cmd)
        self.assertIn("--json-schema", claude_cmd)
        self.assertIn("codex exec", codex_cmd)
        self.assertIn("--output-schema schemas/agent_response.schema.json", codex_cmd)

    def test_detect_available_agents(self) -> None:
        def fake_which(binary: str):
            return "/usr/local/bin/" + binary if binary in {"claude", "codex"} else None

        detected = detect_available_agents(fake_which)
        names = [item["name"] for item in detected]
        self.assertEqual(names, ["claude", "codex"])

    def test_choose_default_command(self) -> None:
        claude_cmd = choose_default_command("claude", "schemas/agent_response.schema.json")
        codex_cmd = choose_default_command("codex", "schemas/agent_response.schema.json")
        self.assertIn("claude -p", claude_cmd)
        self.assertIn("codex exec", codex_cmd)

    def test_collect_two_agents_uses_defaults_and_custom(self) -> None:
        answers = iter([
            "claude",
            "",
            "custom_remote",
            "ssh prod 'codex exec --output-schema schemas/agent_response.schema.json {prompt}'",
        ])
        lines = []

        def fake_input(_: str) -> str:
            return next(answers)

        def fake_print(msg: str) -> None:
            lines.append(msg)

        first, second = collect_two_agents(
            input_fn=fake_input,
            print_fn=fake_print,
            detected=[{"name": "claude"}, {"name": "codex"}],
            schema_path="schemas/agent_response.schema.json",
        )
        self.assertEqual(first["name"], "claude")
        self.assertIn("claude -p", first["command"])
        self.assertEqual(second["name"], "custom_remote")
        self.assertIn("ssh prod", second["command"])

    def test_collect_two_agents_normalizes_bare_agent_binary(self) -> None:
        answers = iter(["claude", "claude", "codex", "codex"])

        def fake_input(_: str) -> str:
            return next(answers)

        def fake_print(_: str) -> None:
            return None

        first, second = collect_two_agents(
            input_fn=fake_input,
            print_fn=fake_print,
            detected=[{"name": "claude"}, {"name": "codex"}],
            schema_path="schemas/agent_response.schema.json",
        )
        self.assertIn("claude -p", first["command"])
        self.assertIn("codex exec", second["command"])

    def test_normalize_command_template_rewrites_bare_binary(self) -> None:
        normalized = normalize_command_template(
            "claude",
            "claude",
            "schemas/agent_response.schema.json",
        )
        self.assertIn("claude -p", normalized)

    def test_save_and_load_agent_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "agents.json"
            first = {"name": "claude", "command": "claude -p {prompt}"}
            second = {"name": "codex", "command": "codex exec {prompt}"}

            save_agent_config(config_path, first, second)
            loaded = load_agent_config(config_path)

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["agent_a"]["name"], "claude")
            self.assertEqual(loaded["agent_b"]["name"], "codex")

    def test_collect_two_agents_can_reuse_saved_config(self) -> None:
        answers = iter([""])
        lines = []
        saved = {
            "agent_a": {"name": "claude", "command": "claude -p {prompt}"},
            "agent_b": {"name": "codex", "command": "codex exec {prompt}"},
        }

        def fake_input(_: str) -> str:
            return next(answers)

        def fake_print(msg: str) -> None:
            lines.append(msg)

        first, second = collect_two_agents(
            input_fn=fake_input,
            print_fn=fake_print,
            detected=[{"name": "claude"}, {"name": "codex"}],
            schema_path="schemas/agent_response.schema.json",
            saved=saved,
        )
        self.assertEqual(first["name"], "claude")
        self.assertEqual(second["name"], "codex")


if __name__ == "__main__":
    unittest.main()
