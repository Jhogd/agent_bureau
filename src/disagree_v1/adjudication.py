from __future__ import annotations

from disagree_v1.models import SessionResult


def build_reconcile_prompt(session: SessionResult) -> str:
    disagreements = "\n".join(f"- [{d.kind}] {d.summary}" for d in session.disagreements)
    return (
        "Reconcile these two agent responses into one plan. "
        "Preserve useful points from both sides and resolve conflicts.\n\n"
        f"Original prompt: {session.prompt}\n\n"
        f"Agent A answer: {session.agent_a.answer}\n"
        f"Agent B answer: {session.agent_b.answer}\n\n"
        f"Disagreements:\n{disagreements if disagreements else '- none'}"
    )


def build_debate_prompt(session: SessionResult, disagreement_index: int) -> str:
    if disagreement_index < 0 or disagreement_index >= len(session.disagreements):
        raise ValueError("Invalid disagreement index")

    target = session.disagreements[disagreement_index]
    return (
        "Debate this disagreement and recommend one choice with rationale.\n\n"
        f"Original prompt: {session.prompt}\n"
        f"Disagreement kind: {target.kind}\n"
        f"Disagreement summary: {target.summary}\n\n"
        f"Agent A answer: {session.agent_a.answer}\n"
        f"Agent B answer: {session.agent_b.answer}"
    )


def apply_action(action: str, orchestrator, session: SessionResult, debate_index: int = 0):
    if action in {"none", "choose_a", "choose_b"}:
        return None
    if action == "reconcile":
        return orchestrator.run(build_reconcile_prompt(session))
    if action == "debate":
        return orchestrator.run(build_debate_prompt(session, debate_index))
    raise ValueError(f"Unsupported action: {action}")
