from __future__ import annotations

from fastapi.testclient import TestClient

from api.service import get_ledger
from scoring.engine import compute_reputation
from tests.helpers import record_transaction


def test_same_owner_decay_applied(
    client: TestClient, registered_agents: list[dict]
) -> None:
    tx_external = record_transaction(
        client,
        requester_agent_id="analyzer-003",
        executor_agent_id="translator-001",
        task_type="translate",
    )
    tx_same_owner = record_transaction(
        client,
        requester_agent_id="summarizer-002",
        executor_agent_id="translator-001",
        task_type="translate",
    )

    response = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_external,
            "evaluator_agent_id": "analyzer-003",
            "evaluated_agent_id": "translator-001",
            "accuracy": 0.95,
            "speed": 0.90,
            "honesty": 0.98,
        },
    )
    assert response.status_code == 200, response.text

    response = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_same_owner,
            "evaluator_agent_id": "summarizer-002",
            "evaluated_agent_id": "translator-001",
            "accuracy": 0.99,
            "speed": 0.99,
            "honesty": 0.99,
        },
    )
    assert response.status_code == 200, response.text

    reputation = client.get("/reputation/translator-001")
    assert reputation.status_code == 200, reputation.text
    accuracy = reputation.json()["reputation"]["requester_rating_accuracy"]

    expected = round((0.95 * 1.0 + 0.99 * 0.3) / 1.3, 4)
    assert accuracy == expected


def test_deterministic_recomputation_from_same_ledger(
    client: TestClient, registered_agents: list[dict]
) -> None:
    tx_id = record_transaction(
        client,
        requester_agent_id="analyzer-003",
        executor_agent_id="translator-001",
        task_type="translate",
        verifier_agent_id="analyzer-003",
        verifier_result="pass",
    )

    response = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_id,
            "evaluator_agent_id": "analyzer-003",
            "evaluated_agent_id": "translator-001",
            "accuracy": 0.95,
            "speed": 0.90,
            "honesty": 0.98,
        },
    )
    assert response.status_code == 200, response.text

    ledger = get_ledger()
    first = compute_reputation(ledger, "translator-001")
    second = compute_reputation(ledger, "translator-001")

    assert first == second
