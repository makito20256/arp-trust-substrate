"""
Agent Reputation Protocol - API Service
========================================
台帳（Ledger）+ スコアリング（Engine）の上に乗る HTTP API。
A2A Extended Agent Card を提供。
"""

from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ledger.transaction_ledger import (
    TransactionLedger,
    TransactionRecord,
    TaskOutcome,
    VerifierResult,
    make_transaction_id,
)
from scoring.engine import compute_reputation, compute_all_reputations


DB_PATH = Path(__file__).parent.parent / "data" / "reputation.db"

_ledger: Optional[TransactionLedger] = None


def get_ledger() -> TransactionLedger:
    global _ledger
    if _ledger is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ledger = TransactionLedger(DB_PATH)
    return _ledger


def reset_ledger(path: str = ":memory:") -> TransactionLedger:
    """テスト用: インメモリ台帳にリセット"""
    global _ledger
    _ledger = TransactionLedger(path)
    return _ledger


# === Request Models ===


class AgentRegistrationRequest(BaseModel):
    agent_id: str
    name: str
    description: str = ""
    endpoint: str = ""
    # Fix #7: default_factory で可変デフォルトを安全に定義
    skills: list[str] = Field(default_factory=list)
    owner_id: Optional[str] = None


class TransactionRequest(BaseModel):
    requester_agent_id: str
    executor_agent_id: str
    task_type: str
    started_at: float
    completed_at: Optional[float] = None
    outcome: str = "success"
    evidence_hash: Optional[str] = None
    verifier_agent_id: Optional[str] = None
    verifier_result: str = "skipped"
    metadata: Optional[dict] = None


class EvaluationRequest(BaseModel):
    transaction_id: str
    evaluator_agent_id: str
    evaluated_agent_id: str
    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    speed: Optional[float] = Field(None, ge=0.0, le=1.0)
    honesty: Optional[float] = Field(None, ge=0.0, le=1.0)


# === FastAPI App ===


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_ledger()
    yield


app = FastAPI(
    title="Agent Reputation Protocol",
    description=(
        "AI経済圏の信用インフラ — "
        "Append-only Ledger + Deterministic Scoring"
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.post("/agents/register")
async def register_agent(req: AgentRegistrationRequest):
    ledger = get_ledger()
    result = ledger.register_agent(
        agent_id=req.agent_id,
        name=req.name,
        description=req.description,
        endpoint=req.endpoint,
        skills=req.skills,
        owner_id=req.owner_id,
    )
    return {"status": "registered", **result}


@app.post("/transactions")
async def record_transaction(req: TransactionRequest):
    ledger = get_ledger()
    tx_id = make_transaction_id()
    try:
        record = TransactionRecord(
            transaction_id=tx_id,
            requester_agent_id=req.requester_agent_id,
            executor_agent_id=req.executor_agent_id,
            task_type=req.task_type,
            started_at=req.started_at,
            completed_at=req.completed_at,
            outcome=TaskOutcome(req.outcome),
            evidence_hash=req.evidence_hash,
            verifier_agent_id=req.verifier_agent_id,
            verifier_result=VerifierResult(req.verifier_result),
            metadata=req.metadata,
        )
        result = ledger.record_transaction(record)
        return {"status": "recorded", **result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/evaluations")
async def record_evaluation(req: EvaluationRequest):
    ledger = get_ledger()
    try:
        result = ledger.record_evaluation(
            transaction_id=req.transaction_id,
            evaluator_agent_id=req.evaluator_agent_id,
            evaluated_agent_id=req.evaluated_agent_id,
            accuracy=req.accuracy,
            speed=req.speed,
            honesty=req.honesty,
        )
        return {"status": "recorded", **result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/reputation/{agent_id}")
async def get_reputation(agent_id: str):
    ledger = get_ledger()
    agent = ledger.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    score = compute_reputation(ledger, agent_id)
    return {"agent_id": agent_id, "reputation": asdict(score)}


@app.get("/search")
async def search_agents(
    min_score: float = 0.0,
    skill: Optional[str] = None,
    limit: int = 20,
):
    ledger = get_ledger()
    all_scores = compute_all_reputations(ledger)
    agents = ledger.list_all_agents()

    results = []
    for agent in agents:
        aid = agent["agent_id"]
        score = all_scores.get(aid)
        if not score:
            continue
        if score.overall < min_score:
            continue
        if skill and skill not in agent.get("skills", []):
            continue
        results.append({
            "agent": agent,
            "reputation": asdict(score),
        })

    results.sort(key=lambda x: x["reputation"]["overall"], reverse=True)
    return {"agents": results[:limit], "count": len(results)}


@app.get("/agent-card/{agent_id}")
async def get_extended_agent_card(agent_id: str):
    """A2A Agent Card + reputation 拡張（A2A extensions 機構準拠）。"""
    ledger = get_ledger()
    agent = ledger.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")

    score = compute_reputation(ledger, agent_id)

    return {
        "name": agent["name"],
        "description": agent["description"],
        "url": agent["endpoint"],
        "version": "1.0.0",
        "skills": [{"id": s, "description": s} for s in agent["skills"]],
        "extensions": [
            {
                "uri": (
                    "https://agent-reputation-protocol.dev"
                    "/extensions/reputation/v0.1"
                ),
                "required": False,
                "config": {
                    "scores": {
                        "success_rate": score.success_rate,
                        "accuracy": score.requester_rating_accuracy,
                        "speed": score.requester_rating_speed,
                        "honesty": score.requester_rating_honesty,
                    },
                    "overall": score.overall,
                    "confidence": score.confidence,
                    "total_transactions": score.total_transactions,
                    "total_evaluations": score.total_evaluations,
                    "verifier_pass_rate": score.verifier_pass_rate,
                },
            }
        ],
    }


@app.get("/stats")
async def get_stats():
    return get_ledger().stats()


@app.get("/transactions/{agent_id}")
async def get_agent_transactions(agent_id: str):
    ledger = get_ledger()
    txs = ledger.get_transactions_for(agent_id)
    return {"agent_id": agent_id, "transactions": txs, "count": len(txs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
