from __future__ import annotations

import time

from fastapi.testclient import TestClient

from ledger.transaction_ledger import make_evidence_hash


def record_transaction(
    client: TestClient,
    requester_agent_id: str,
    executor_agent_id: str,
    task_type: str,
    *,
    verifier_agent_id: str | None = None,
    verifier_result: str = "skipped",
    outcome: str = "success",
) -> str:
    now = time.time()
    response = client.post(
        "/transactions",
        json={
            "requester_agent_id": requester_agent_id,
            "executor_agent_id": executor_agent_id,
            "task_type": task_type,
            "started_at": now - 5,
            "completed_at": now,
            "outcome": outcome,
            "evidence_hash": make_evidence_hash(
                f"{requester_agent_id}:{executor_agent_id}:{task_type}:{now}"
            ),
            "verifier_agent_id": verifier_agent_id,
            "verifier_result": verifier_result,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["transaction_id"]
