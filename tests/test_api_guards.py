from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import record_transaction


def test_empty_evaluation_rejected(
    client: TestClient, registered_agents: list[dict]
) -> None:
    tx_id = record_transaction(
        client,
        requester_agent_id="translator-001",
        executor_agent_id="analyzer-003",
        task_type="analyze",
    )

    response = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_id,
            "evaluator_agent_id": "translator-001",
            "evaluated_agent_id": "analyzer-003",
        },
    )

    assert response.status_code == 400
    assert "At least one" in response.text


def test_self_evaluation_rejected(
    client: TestClient, registered_agents: list[dict]
) -> None:
    tx_id = record_transaction(
        client,
        requester_agent_id="translator-001",
        executor_agent_id="analyzer-003",
        task_type="analyze",
    )

    response = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_id,
            "evaluator_agent_id": "translator-001",
            "evaluated_agent_id": "translator-001",
            "accuracy": 1.0,
        },
    )

    assert response.status_code == 400
    assert "Self-evaluation not allowed" in response.text


def test_duplicate_evaluation_rejected(
    client: TestClient, registered_agents: list[dict]
) -> None:
    tx_id = record_transaction(
        client,
        requester_agent_id="analyzer-003",
        executor_agent_id="translator-001",
        task_type="translate",
    )

    first = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_id,
            "evaluator_agent_id": "analyzer-003",
            "evaluated_agent_id": "translator-001",
            "accuracy": 0.95,
        },
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_id,
            "evaluator_agent_id": "analyzer-003",
            "evaluated_agent_id": "translator-001",
            "accuracy": 0.75,
        },
    )

    assert second.status_code == 400
    assert "Duplicate evaluation" in second.text


def test_unregistered_verifier_rejected(
    client: TestClient, registered_agents: list[dict]
) -> None:
    response = client.post(
        "/transactions",
        json={
            "requester_agent_id": "translator-001",
            "executor_agent_id": "analyzer-003",
            "task_type": "analyze",
            "started_at": 1.0,
            "completed_at": 2.0,
            "outcome": "success",
            "verifier_agent_id": "ghost-agent-999",
            "verifier_result": "pass",
        },
    )

    assert response.status_code == 400
    assert "not registered" in response.text
