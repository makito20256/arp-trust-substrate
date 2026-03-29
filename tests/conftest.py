from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.service import app, reset_ledger  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    reset_ledger(":memory:")
    return TestClient(app)


@pytest.fixture()
def registered_agents(client: TestClient) -> list[dict]:
    agents = [
        {
            "agent_id": "translator-001",
            "name": "TranslateBot",
            "description": "JP/EN translation",
            "endpoint": "http://localhost:8001/a2a",
            "skills": ["translate"],
            "owner_id": "owner-alice",
        },
        {
            "agent_id": "summarizer-002",
            "name": "SummaryBot",
            "description": "Summaries",
            "endpoint": "http://localhost:8002/a2a",
            "skills": ["summarize"],
            "owner_id": "owner-alice",
        },
        {
            "agent_id": "analyzer-003",
            "name": "AnalyzeBot",
            "description": "Analysis",
            "endpoint": "http://localhost:8003/a2a",
            "skills": ["analyze"],
            "owner_id": "owner-bob",
        },
    ]
    for agent in agents:
        response = client.post("/agents/register", json=agent)
        assert response.status_code == 200, response.text
    return agents

