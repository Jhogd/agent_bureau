from __future__ import annotations

from disagree_v1.models import AgentResponse, Disagreement


CONFIDENCE_GAP_THRESHOLD = 0.30


def _normalize(items: list[str]) -> set[str]:
    return {item.strip().lower() for item in items if item.strip()}


def classify_disagreements(agent_a: AgentResponse, agent_b: AgentResponse) -> list[Disagreement]:
    disagreements: list[Disagreement] = []

    if _normalize(agent_a.proposed_actions) != _normalize(agent_b.proposed_actions):
        disagreements.append(
            Disagreement(
                kind="approach",
                summary="Agents propose different implementation approaches.",
            )
        )

    assumption_delta = _normalize(agent_a.assumptions) ^ _normalize(agent_b.assumptions)
    if assumption_delta:
        disagreements.append(
            Disagreement(
                kind="fact",
                summary="Agents rely on different assumptions about constraints.",
            )
        )

    confidence_gap = abs(agent_a.confidence - agent_b.confidence)
    if confidence_gap >= CONFIDENCE_GAP_THRESHOLD:
        disagreements.append(
            Disagreement(
                kind="confidence_gap",
                summary=f"Confidence differs by {confidence_gap:.2f}.",
            )
        )

    return disagreements
