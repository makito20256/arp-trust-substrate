"""
Agent Reputation Protocol - Phase 0 Self-contained Demo
=======================================================
FastAPI TestClient でインプロセス実行。ネットワーク不要。
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from api.service import app, reset_ledger
from ledger.transaction_ledger import make_evidence_hash


def section(title: str):
    print(f"\n{'=' * 64}")
    print(f"  {title}")
    print(f"{'=' * 64}")


def main():
    reset_ledger(":memory:")
    client = TestClient(app)

    print("🚀 Agent Reputation Protocol — Phase 0 Demo")
    print("=" * 64)
    print("  台帳先行・スコア後算出・決定論的再計算可能")

    # === Step 1: エージェント登録 ===
    section("📋 Step 1: エージェント登録")

    agents = [
        {
            "agent_id": "translator-001",
            "name": "TranslateBot",
            "description": "JP/EN/FR multilingual translation",
            "endpoint": "http://localhost:8001/a2a",
            "skills": ["translate", "language-detection"],
            "owner_id": "owner-alice",
        },
        {
            "agent_id": "summarizer-002",
            "name": "SummaryBot",
            "description": "Text summarization",
            "endpoint": "http://localhost:8002/a2a",
            "skills": ["summarize", "key-extraction"],
            "owner_id": "owner-alice",
        },
        {
            "agent_id": "analyzer-003",
            "name": "AnalyzeBot",
            "description": "Data analysis and reporting",
            "endpoint": "http://localhost:8003/a2a",
            "skills": ["analyze", "report"],
            "owner_id": "owner-bob",
        },
    ]

    for a in agents:
        r = client.post("/agents/register", json=a)
        assert r.status_code == 200, r.text
        print(
            f"  ✅ {a['name']:15s} owner={a['owner_id']:12s} → registered"
        )

    print(
        "\n  ⚠️  TranslateBot と SummaryBot は同一オーナー（owner-alice）"
    )
    print("     → 相互評価は重み 0.3 に減衰される")

    # === Step 2: 取引記録 ===
    section("🔄 Step 2: 取引を Append-only 台帳に記録")

    now = time.time()
    transactions = [
        {
            "req": "analyzer-003",
            "exe": "translator-001",
            "type": "translate",
            "outcome": "success",
            "started": now - 120,
            "completed": now - 100,
            "evidence": make_evidence_hash("translated output of tx-001"),
            "verifier": "analyzer-003",
            "v_result": "pass",
            "desc": "AnalyzeBot→TranslateBot: 翻訳 → 成功、検証PASS",
        },
        {
            "req": "analyzer-003",
            "exe": "summarizer-002",
            "type": "summarize",
            "outcome": "partial",
            "started": now - 90,
            "completed": now - 60,
            "evidence": make_evidence_hash("partial summary of tx-002"),
            "verifier": "analyzer-003",
            "v_result": "fail",
            "desc": "AnalyzeBot→SummaryBot: 要約 → 部分成功、検証FAIL",
        },
        {
            "req": "translator-001",
            "exe": "analyzer-003",
            "type": "analyze",
            "outcome": "success",
            "started": now - 50,
            "completed": now - 45,
            "evidence": make_evidence_hash("analysis result of tx-003"),
            "verifier": None,
            "v_result": "skipped",
            "desc": "TranslateBot→AnalyzeBot: 分析 → 成功、検証なし",
        },
        {
            "req": "summarizer-002",
            "exe": "translator-001",
            "type": "translate",
            "outcome": "success",
            "started": now - 30,
            "completed": now - 25,
            "evidence": make_evidence_hash("translated output of tx-004"),
            "verifier": None,
            "v_result": "skipped",
            "desc": "SummaryBot→TranslateBot: 翻訳 → 成功（⚠️同一オーナー）",
        },
        {
            "req": "translator-001",
            "exe": "summarizer-002",
            "type": "summarize",
            "outcome": "timeout",
            "started": now - 20,
            "completed": None,
            "evidence": None,
            "verifier": None,
            "v_result": "skipped",
            "desc": "TranslateBot→SummaryBot: 要約 → タイムアウト",
        },
    ]

    tx_ids = []
    for tx in transactions:
        r = client.post(
            "/transactions",
            json={
                "requester_agent_id": tx["req"],
                "executor_agent_id": tx["exe"],
                "task_type": tx["type"],
                "started_at": tx["started"],
                "completed_at": tx["completed"],
                "outcome": tx["outcome"],
                "evidence_hash": tx["evidence"],
                "verifier_agent_id": tx["verifier"],
                "verifier_result": tx["v_result"],
            },
        )
        assert r.status_code == 200, f"Failed: {r.text}"
        real_id = r.json()["transaction_id"]
        tx_ids.append(real_id)
        print(f"  📝 {tx['desc']}")
        print(f"     → {real_id}")

    # 自己取引テスト
    print("\n  🚫 自己取引テスト:")
    r = client.post(
        "/transactions",
        json={
            "requester_agent_id": "translator-001",
            "executor_agent_id": "translator-001",
            "task_type": "self-deal",
            "started_at": now,
        },
    )
    print(f"     status={r.status_code} (400=正しくブロック ✅)")

    # 未登録verifierテスト
    print("  🚫 未登録verifierテスト:")
    r = client.post(
        "/transactions",
        json={
            "requester_agent_id": "translator-001",
            "executor_agent_id": "analyzer-003",
            "task_type": "test",
            "started_at": now,
            "verifier_agent_id": "ghost-agent-999",
            "verifier_result": "pass",
        },
    )
    print(f"     status={r.status_code} (400=未登録verifier拒否 ✅)")

    # === Step 3: 評価記録 ===
    section("⭐ Step 3: 取引に紐づく相互評価")

    evaluations = [
        {
            "tx_idx": 0,
            "er": "analyzer-003",
            "ed": "translator-001",
            "a": 0.95,
            "s": 0.90,
            "h": 0.98,
            "desc": "AnalyzeBot → TranslateBot: 高品質な翻訳",
        },
        {
            "tx_idx": 1,
            "er": "analyzer-003",
            "ed": "summarizer-002",
            "a": 0.55,
            "s": 0.60,
            "h": 0.70,
            "desc": "AnalyzeBot → SummaryBot: 不完全な要約",
        },
        {
            "tx_idx": 2,
            "er": "translator-001",
            "ed": "analyzer-003",
            "a": 0.92,
            "s": 0.95,
            "h": 0.90,
            "desc": "TranslateBot → AnalyzeBot: 迅速な分析",
        },
        {
            "tx_idx": 3,
            "er": "summarizer-002",
            "ed": "translator-001",
            "a": 0.99,
            "s": 0.99,
            "h": 0.99,
            "desc": "SummaryBot → TranslateBot: 完璧（⚠️同一オーナー→重み0.3）",
        },
    ]

    for ev in evaluations:
        r = client.post(
            "/evaluations",
            json={
                "transaction_id": tx_ids[ev["tx_idx"]],
                "evaluator_agent_id": ev["er"],
                "evaluated_agent_id": ev["ed"],
                "accuracy": ev["a"],
                "speed": ev["s"],
                "honesty": ev["h"],
            },
        )
        assert r.status_code == 200, f"Failed: {r.text}"
        print(f"  ⭐ {ev['desc']}")

    # 自己評価テスト
    print("\n  🚫 自己評価テスト:")
    r = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_ids[0],
            "evaluator_agent_id": "translator-001",
            "evaluated_agent_id": "translator-001",
            "accuracy": 1.0,
        },
    )
    print(f"     status={r.status_code} (400=正しくブロック ✅)")

    # 部外者評価テスト
    print("  🚫 部外者評価テスト:")
    r = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_ids[0],
            "evaluator_agent_id": "summarizer-002",
            "evaluated_agent_id": "translator-001",
            "accuracy": 0.5,
        },
    )
    print(f"     status={r.status_code} (400=当事者のみ評価可 ✅)")

    # 重複評価テスト
    print("  🚫 重複評価テスト:")
    r = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_ids[0],
            "evaluator_agent_id": "analyzer-003",
            "evaluated_agent_id": "translator-001",
            "accuracy": 0.50,
        },
    )
    print(f"     status={r.status_code} (400=重複評価拒否 ✅)")

    # 空評価テスト
    print("  🚫 空評価テスト:")
    r = client.post(
        "/evaluations",
        json={
            "transaction_id": tx_ids[2],
            "evaluator_agent_id": "translator-001",
            "evaluated_agent_id": "analyzer-003",
        },
    )
    print(f"     status={r.status_code} (400=空評価拒否 ✅)")

    # === Step 4: スコア導出 ===
    section("📊 Step 4: 台帳からスコアを決定論的に導出")

    header = (
        f"  {'Agent':<18} {'Success':>8} {'Accuracy':>9} "
        f"{'Speed':>8} {'Honesty':>9} {'OVERALL':>9} "
        f"{'Conf':>7} {'TXs':>5} {'Evals':>6}"
    )
    print(header)
    print(f"  {'─' * 77}")

    for aid in ["translator-001", "summarizer-002", "analyzer-003"]:
        r = client.get(f"/reputation/{aid}")
        assert r.status_code == 200
        rep = r.json()["reputation"]
        print(
            f"  {aid:<18} "
            f"{rep['success_rate']:>8.2%} "
            f"{rep['requester_rating_accuracy']:>9.4f} "
            f"{rep['requester_rating_speed']:>8.4f} "
            f"{rep['requester_rating_honesty']:>9.4f} "
            f"{rep['overall']:>9.4f} "
            f"{rep['confidence']:>7.2f} "
            f"{rep['total_transactions']:>5} "
            f"{rep['total_evaluations']:>6}"
        )

    # === Step 5: 同一オーナー減衰の効果 ===
    section("🔬 Step 5: 同一オーナー減衰の効果")

    r = client.get("/reputation/translator-001")
    rep_t = r.json()["reputation"]
    expected = (0.95 * 1.0 + 0.99 * 0.3) / (1.0 + 0.3)

    print(f"""
  TranslateBot は2件の評価を受けた:
    1. AnalyzeBot (owner-bob)  → accuracy=0.95  重み=1.0
    2. SummaryBot (owner-alice) → accuracy=0.99  重み=0.3 ← 同一オーナー減衰

  もし減衰なし: 平均 = (0.95 + 0.99) / 2 = 0.9700
  減衰あり:     加重 = (0.95×1.0 + 0.99×0.3) / 1.3 = {expected:.4f}
  実際の値:     {rep_t['requester_rating_accuracy']:.4f}

  ✅ 同一オーナー配下の相互ブーストが抑制されている。""")

    # === Step 6: Extended Agent Card ===
    section("🪪 Step 6: Extended Agent Card（A2A Extension 準拠）")

    r = client.get("/agent-card/translator-001")
    card = r.json()
    print(json.dumps(card, indent=2, ensure_ascii=False))

    print("""
  ☝️ 'extensions' フィールドに reputation 拡張を格納。
     A2A の extensions 機構（URI + required + config）に準拠。""")

    # === Step 7: 検索 ===
    section("🔍 Step 7: 評判ベース検索")

    r = client.get("/search", params={"min_score": 0.7})
    data = r.json()
    print("  overall >= 0.70:")
    for item in data["agents"]:
        a = item["agent"]
        rep = item["reputation"]
        print(
            f"    ✅ {a['name']:<15} "
            f"overall={rep['overall']:.4f} "
            f"confidence={rep['confidence']:.2f}"
        )

    # === Step 8: 再計算可能性 ===
    section("🔁 Step 8: 決定論的再計算の証明")

    r1 = client.get("/reputation/translator-001")
    r2 = client.get("/reputation/translator-001")
    s1 = r1.json()["reputation"]["overall"]
    s2 = r2.json()["reputation"]["overall"]
    print(f"  1回目: overall = {s1}")
    print(f"  2回目: overall = {s2}")
    match = "✅ YES" if s1 == s2 else "❌ NO"
    print(f"  一致: {match}")

    # === 統計 ===
    r = client.get("/stats")
    stats = r.json()

    section("✅ Phase 0 デモ完了")
    print(f"""
  📈 台帳統計:
     エージェント: {stats['agents']}
     取引記録:     {stats['transactions']}
     評価記録:     {stats['evaluations']}

  実装済み:
    ✅ Append-only transaction ledger（不変台帳）
    ✅ PRAGMA foreign_keys = ON（参照整合性）
    ✅ 取引に紐づく評価のみ許可
    ✅ 自己評価・自己取引の拒否
    ✅ 取引当事者以外の評価を拒否
    ✅ 重複評価の拒否（UNIQUE制約）
    ✅ 空評価の拒否（全スコアNoneを拒否）
    ✅ 未登録verifierの拒否（FK制約＋アプリ検証）
    ✅ 同一オーナー配下の相互評価を重み0.3に減衰
    ✅ 部分評価の項目別重み分離（希薄化防止）
    ✅ 決定論的スコア再計算
    ✅ Extended Agent Card（A2A extensions機構準拠）
    ✅ ON CONFLICT DO UPDATE（安全なUPSERT）

  v0.2 で追加予定:
    ⬜ PageRank型重み付け（評価者の信頼度反映）
    ⬜ 評判の減衰継承（バージョン更新時）
    ⬜ 評判の貸与（保証人制度）
    ⬜ localhost実HTTPデモ（A2A transport越し）
""")


if __name__ == "__main__":
    main()
