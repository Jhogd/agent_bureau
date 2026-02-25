from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from disagree_v1.adapters import AgentAdapter
from disagree_v1.classifier import classify_disagreements
from disagree_v1.models import SessionResult
from disagree_v1.store import JsonlSessionStore


class DisagreementOrchestrator:
    def __init__(
        self,
        agent_a: AgentAdapter,
        agent_b: AgentAdapter,
        session_store: JsonlSessionStore,
    ):
        self._agent_a = agent_a
        self._agent_b = agent_b
        self._session_store = session_store

    def run(self, prompt: str) -> SessionResult:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(self._agent_a.run, prompt)
            future_b = executor.submit(self._agent_b.run, prompt)
            response_a = future_a.result()
            response_b = future_b.result()

        disagreements = classify_disagreements(response_a, response_b)
        session = SessionResult(
            prompt=prompt,
            agent_a=response_a,
            agent_b=response_b,
            disagreements=disagreements,
        )
        self._session_store.append(session.to_dict())
        return session
