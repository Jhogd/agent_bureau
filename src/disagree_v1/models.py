from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AgentResponse:
    answer: str
    proposed_actions: list[str]
    assumptions: list[str]
    confidence: float


@dataclass(frozen=True)
class Disagreement:
    kind: str
    summary: str


@dataclass(frozen=True)
class SessionResult:
    prompt: str
    agent_a: AgentResponse
    agent_b: AgentResponse
    disagreements: list[Disagreement]

    def to_dict(self) -> dict[str, object]:
        return {
            "prompt": self.prompt,
            "agent_a": asdict(self.agent_a),
            "agent_b": asdict(self.agent_b),
            "disagreements": [asdict(item) for item in self.disagreements],
        }
