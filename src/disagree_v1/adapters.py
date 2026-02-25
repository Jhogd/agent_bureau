from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from typing import Callable, Protocol

from disagree_v1.models import AgentResponse


class AgentAdapter(Protocol):
    def run(self, prompt: str) -> AgentResponse:
        ...


@dataclass
class StubAgentAdapter:
    """Deterministic local adapter for CLI/demo mode."""

    profile: str

    def run(self, prompt: str) -> AgentResponse:
        if self.profile == "architecture":
            return AgentResponse(
                answer=f"Architecture-first response for: {prompt}",
                proposed_actions=[
                    "Define bounded interfaces",
                    "Introduce async work queue",
                ],
                assumptions=["Background workers are allowed"],
                confidence=0.78,
            )

        return AgentResponse(
            answer=f"Delivery-first response for: {prompt}",
            proposed_actions=[
                "Keep synchronous path",
                "Add focused tests",
            ],
            assumptions=["Keep infrastructure minimal"],
            confidence=0.62,
        )


def _default_runner(args: list[str]) -> str:
    try:
        completed = subprocess.run(args, check=True, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired as exc:
        command = " ".join(args[:3])
        raise ValueError(f"Command timed out: {command} ...") from exc
    return completed.stdout.strip()


@dataclass
class CommandJsonAdapter:
    """Runs an external command and expects JSON payload for AgentResponse."""

    name: str
    command_template: str
    runner: Callable[[list[str]], str] = _default_runner

    def _build_args(self, prompt: str) -> list[str]:
        args = shlex.split(self.command_template)
        if "{prompt}" in args:
            return [prompt if token == "{prompt}" else token for token in args]
        args.append(prompt)
        return args

    def run(self, prompt: str) -> AgentResponse:
        raw = self.runner(self._build_args(prompt))
        payload = self._parse_payload(raw)
        return self._validate_payload(payload)

    def _parse_payload(self, raw: str) -> dict[str, object]:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and start < end:
            candidate = raw[start : end + 1]
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{self.name} returned non-JSON output") from exc
            if isinstance(parsed, dict):
                return parsed

        raise ValueError(f"{self.name} returned non-JSON output")

    def _validate_payload(self, payload: dict[str, object]) -> AgentResponse:
        required = {"answer", "proposed_actions", "assumptions", "confidence"}
        if not required.issubset(payload.keys()):
            raise ValueError(f"{self.name} JSON missing required keys")

        answer = payload["answer"]
        proposed_actions = payload["proposed_actions"]
        assumptions = payload["assumptions"]
        confidence = payload["confidence"]

        if not isinstance(answer, str):
            raise ValueError(f"{self.name} answer must be a string")
        if not isinstance(proposed_actions, list) or not all(isinstance(i, str) for i in proposed_actions):
            raise ValueError(f"{self.name} proposed_actions must be a list[str]")
        if not isinstance(assumptions, list) or not all(isinstance(i, str) for i in assumptions):
            raise ValueError(f"{self.name} assumptions must be a list[str]")

        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{self.name} confidence must be numeric") from exc

        return AgentResponse(
            answer=answer,
            proposed_actions=proposed_actions,
            assumptions=assumptions,
            confidence=confidence_value,
        )
