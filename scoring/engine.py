"""
Scoring Engine v0 - 台帳から決定論的にスコアを導出
=================================================
設計原則:
- 台帳（TransactionLedger）のデータのみから計算
- 同じ台帳に対して何度計算しても同じ結果（deterministic）
- v0 は単純な重み付き平均。PageRank は v0.2 で追加予定。

スコア構成:
- success_rate:       取引の成功率（台帳から直接）
- avg_latency_score:  平均所要時間を 0-1 にスケール
- verifier_pass_rate: 第三者検証の通過率（台帳から直接）
- requester_rating:   依頼者からの評価平均（評価台帳から）
- overall:            上記の加重平均

談合防止:
- 自己評価は台帳レベルで拒否済み
- 同一オーナー配下の相互評価は重みを 0.3 に減衰
"""

from dataclasses import dataclass
from typing import Optional

from ledger.transaction_ledger import TransactionLedger


@dataclass
class ReputationScore:
    agent_id: str
    success_rate: float
    avg_latency_score: float
    verifier_pass_rate: Optional[float]
    requester_rating_accuracy: float
    requester_rating_speed: float
    requester_rating_honesty: float
    overall: float
    total_transactions: int
    total_evaluations: int
    confidence: float


SAME_OWNER_DECAY = 0.3
LATENCY_BASELINE_SEC = 60.0

WEIGHTS = {
    "success_rate": 0.25,
    "verifier_pass_rate": 0.20,
    "rating_accuracy": 0.25,
    "rating_honesty": 0.15,
    "rating_speed": 0.10,
    "latency": 0.05,
}


def compute_reputation(
    ledger: TransactionLedger, agent_id: str,
) -> ReputationScore:
    """台帳から決定論的にスコアを計算する。"""
    stats = ledger.get_agent_stats(agent_id)
    evaluations = ledger.get_evaluations_for(agent_id)

    success_rate = stats["success_rate"]

    avg_dur = stats["avg_duration_sec"]
    if avg_dur is not None and avg_dur >= 0:
        latency_score = max(0.0, 1.0 - (avg_dur / LATENCY_BASELINE_SEC))
    else:
        latency_score = 0.5

    verifier_pass_rate = stats["verifier_pass_rate"]

    # Fix #5: 項目ごとに sum と weight を分離
    # accuracy が None の評価の重みが speed/honesty の分母に混ざらないようにする
    acc_sum, acc_weight = 0.0, 0.0
    spd_sum, spd_weight = 0.0, 0.0
    hon_sum, hon_weight = 0.0, 0.0

    for ev in evaluations:
        w = 1.0
        if ledger.check_same_owner(ev["evaluator_agent_id"], agent_id):
            w = SAME_OWNER_DECAY

        if ev["accuracy"] is not None:
            acc_sum += ev["accuracy"] * w
            acc_weight += w
        if ev["speed"] is not None:
            spd_sum += ev["speed"] * w
            spd_weight += w
        if ev["honesty"] is not None:
            hon_sum += ev["honesty"] * w
            hon_weight += w

    avg_accuracy = acc_sum / acc_weight if acc_weight > 0 else 0.5
    avg_speed = spd_sum / spd_weight if spd_weight > 0 else 0.5
    avg_honesty = hon_sum / hon_weight if hon_weight > 0 else 0.5

    # confidence
    tx_confidence = min(1.0, stats["total_executed"] / 20.0)
    eval_confidence = min(1.0, len(evaluations) / 10.0)
    confidence = (tx_confidence + eval_confidence) / 2.0

    # overall
    components = {
        "success_rate": success_rate,
        "rating_accuracy": avg_accuracy,
        "rating_honesty": avg_honesty,
        "rating_speed": avg_speed,
        "latency": latency_score,
    }

    if verifier_pass_rate is not None:
        components["verifier_pass_rate"] = verifier_pass_rate
        active_weights = WEIGHTS
    else:
        active_weights = {
            k: v for k, v in WEIGHTS.items() if k != "verifier_pass_rate"
        }

    total_weight = sum(active_weights.values())
    overall = sum(
        components[k] * (active_weights[k] / total_weight)
        for k in active_weights
        if k in components
    )

    return ReputationScore(
        agent_id=agent_id,
        success_rate=round(success_rate, 4),
        avg_latency_score=round(latency_score, 4),
        verifier_pass_rate=(
            round(verifier_pass_rate, 4)
            if verifier_pass_rate is not None
            else None
        ),
        requester_rating_accuracy=round(avg_accuracy, 4),
        requester_rating_speed=round(avg_speed, 4),
        requester_rating_honesty=round(avg_honesty, 4),
        overall=round(overall, 4),
        total_transactions=stats["total_executed"],
        total_evaluations=len(evaluations),
        confidence=round(confidence, 4),
    )


def compute_all_reputations(
    ledger: TransactionLedger,
) -> dict[str, ReputationScore]:
    agents = ledger.list_all_agents()
    return {
        a["agent_id"]: compute_reputation(ledger, a["agent_id"])
        for a in agents
    }
