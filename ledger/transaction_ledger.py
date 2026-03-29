"""
Transaction Ledger - Append-only 経済ログ基盤
=============================================
評判スコアはこの台帳から「再計算」される。
台帳自体は不変（append-only）。削除・更新なし。

設計原則:
- 全ての取引イベントは不変レコードとして記録
- 同じ台帳から何度再計算しても同じスコアが出る（deterministic）
- 評価は取引に紐づく（取引なしの評価は存在しない）
- evidence_hash で成果物の存在を証明可能
"""

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class TaskOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class VerifierResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    INCONCLUSIVE = "inconclusive"


@dataclass
class TransactionRecord:
    """不変の取引レコード。一度書いたら変更しない。"""
    transaction_id: str
    requester_agent_id: str
    executor_agent_id: str
    task_type: str
    started_at: float
    completed_at: Optional[float] = None
    outcome: TaskOutcome = TaskOutcome.SUCCESS
    evidence_hash: Optional[str] = None
    verifier_agent_id: Optional[str] = None
    verifier_result: VerifierResult = VerifierResult.SKIPPED
    metadata: Optional[dict] = None


class TransactionLedger:
    """
    Append-only 取引台帳。

    不変保証:
    - INSERT のみ。UPDATE / DELETE は存在しない（agents 除く）。
    - 再計算可能: 全スコアはこの台帳から導出される。
    """

    def __init__(self, db_path: str | Path = ":memory:"):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Fix #3: 外部キー制約を有効化
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                endpoint TEXT,
                skills TEXT,
                owner_id TEXT,
                registered_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                requester_agent_id TEXT NOT NULL,
                executor_agent_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                started_at REAL NOT NULL,
                completed_at REAL,
                outcome TEXT NOT NULL DEFAULT 'success',
                evidence_hash TEXT,
                verifier_agent_id TEXT,
                verifier_result TEXT NOT NULL DEFAULT 'skipped',
                metadata TEXT,
                recorded_at REAL NOT NULL,
                FOREIGN KEY (requester_agent_id) REFERENCES agents(agent_id),
                FOREIGN KEY (executor_agent_id) REFERENCES agents(agent_id),
                FOREIGN KEY (verifier_agent_id) REFERENCES agents(agent_id)
            );

            CREATE TABLE IF NOT EXISTS evaluations (
                evaluation_id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                evaluator_agent_id TEXT NOT NULL,
                evaluated_agent_id TEXT NOT NULL,
                accuracy REAL,
                speed REAL,
                honesty REAL,
                created_at REAL NOT NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
                FOREIGN KEY (evaluator_agent_id) REFERENCES agents(agent_id),
                FOREIGN KEY (evaluated_agent_id) REFERENCES agents(agent_id),
                -- Fix #4: 同一取引に対する同一評価者→被評価者の重複を防止
                UNIQUE (transaction_id, evaluator_agent_id, evaluated_agent_id)
            );

            CREATE INDEX IF NOT EXISTS idx_tx_executor
                ON transactions(executor_agent_id);
            CREATE INDEX IF NOT EXISTS idx_tx_requester
                ON transactions(requester_agent_id);
            CREATE INDEX IF NOT EXISTS idx_eval_evaluated
                ON evaluations(evaluated_agent_id);
            CREATE INDEX IF NOT EXISTS idx_eval_transaction
                ON evaluations(transaction_id);
        """)
        self.conn.commit()

    # === Agent Registration ===

    def register_agent(
        self, agent_id: str, name: str, description: str = "",
        endpoint: str = "", skills: Optional[list[str]] = None,
        owner_id: Optional[str] = None,
    ) -> dict:
        now = time.time()
        # Fix #6: INSERT OR REPLACE → ON CONFLICT DO UPDATE
        # registered_at は初回登録時のみ設定、以後は上書きしない
        self.conn.execute(
            """INSERT INTO agents
               (agent_id, name, description, endpoint, skills, owner_id, registered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(agent_id) DO UPDATE SET
                   name = excluded.name,
                   description = excluded.description,
                   endpoint = excluded.endpoint,
                   skills = excluded.skills,
                   owner_id = excluded.owner_id""",
            (agent_id, name, description, endpoint,
             json.dumps(skills if skills is not None else []),
             owner_id, now),
        )
        self.conn.commit()
        # Fix #3: 返却値はDB上の実際の registered_at を返す
        row = self.conn.execute(
            "SELECT registered_at FROM agents WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        return {"agent_id": agent_id, "registered_at": row[0]}

    def get_agent(self, agent_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["skills"] = json.loads(d["skills"]) if d["skills"] else []
        return d

    # === Transaction Recording ===

    def record_transaction(self, record: TransactionRecord) -> dict:
        """取引を台帳に追記。不変。"""
        if record.requester_agent_id == record.executor_agent_id:
            raise ValueError("Self-transaction not allowed")

        # requester / executor が登録済みか確認
        for aid in [record.requester_agent_id, record.executor_agent_id]:
            if not self.get_agent(aid):
                raise ValueError(f"Agent {aid} not registered")

        # Fix #3: verifier_agent_id も登録済みか確認
        if record.verifier_agent_id is not None:
            if not self.get_agent(record.verifier_agent_id):
                raise ValueError(
                    f"Verifier agent {record.verifier_agent_id} not registered"
                )

        now = time.time()
        self.conn.execute(
            """INSERT INTO transactions
               (transaction_id, requester_agent_id, executor_agent_id,
                task_type, started_at, completed_at, outcome,
                evidence_hash, verifier_agent_id, verifier_result,
                metadata, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.transaction_id, record.requester_agent_id,
             record.executor_agent_id, record.task_type,
             record.started_at, record.completed_at,
             record.outcome.value, record.evidence_hash,
             record.verifier_agent_id, record.verifier_result.value,
             json.dumps(record.metadata) if record.metadata else None, now),
        )
        self.conn.commit()
        return {"transaction_id": record.transaction_id, "recorded_at": now}

    def get_transaction(self, transaction_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM transactions WHERE transaction_id = ?",
            (transaction_id,),
        ).fetchone()
        return dict(row) if row else None

    # === Evaluation Recording ===

    def record_evaluation(
        self, transaction_id: str, evaluator_agent_id: str,
        evaluated_agent_id: str, accuracy: Optional[float] = None,
        speed: Optional[float] = None, honesty: Optional[float] = None,
    ) -> dict:
        """取引に紐づく評価を記録。"""
        tx = self.get_transaction(transaction_id)
        if not tx:
            raise ValueError(f"Transaction {transaction_id} not found")

        if evaluator_agent_id == evaluated_agent_id:
            raise ValueError("Self-evaluation not allowed")

        # Fix #2: 全スコアが None の空評価を拒否
        if accuracy is None and speed is None and honesty is None:
            raise ValueError(
                "At least one of accuracy, speed, honesty must be provided"
            )

        # 取引の当事者のみが評価可能
        parties = {tx["requester_agent_id"], tx["executor_agent_id"]}
        if tx["verifier_agent_id"]:
            parties.add(tx["verifier_agent_id"])
        if evaluator_agent_id not in parties:
            raise ValueError(
                f"Evaluator {evaluator_agent_id} is not a party "
                f"to transaction {transaction_id}"
            )
        if evaluated_agent_id not in parties:
            raise ValueError(
                f"Evaluated {evaluated_agent_id} is not a party "
                f"to transaction {transaction_id}"
            )

        # スコア範囲チェック
        for val, name in [
            (accuracy, "accuracy"), (speed, "speed"), (honesty, "honesty"),
        ]:
            if val is not None and not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be between 0.0 and 1.0, got {val}")

        eval_id = f"eval-{uuid.uuid4().hex[:12]}"
        now = time.time()
        try:
            self.conn.execute(
                """INSERT INTO evaluations
                   (evaluation_id, transaction_id, evaluator_agent_id,
                    evaluated_agent_id, accuracy, speed, honesty, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (eval_id, transaction_id, evaluator_agent_id,
                 evaluated_agent_id, accuracy, speed, honesty, now),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            # Fix #4: 重複評価をブロック
            raise ValueError(
                f"Duplicate evaluation: {evaluator_agent_id} has already "
                f"evaluated {evaluated_agent_id} for transaction {transaction_id}"
            )
        return {"evaluation_id": eval_id, "created_at": now}

    # === Query Methods (read-only) ===

    def get_evaluations_for(self, agent_id: str) -> list[dict]:
        """あるエージェントが受けた全評価を取得"""
        rows = self.conn.execute(
            """SELECT e.*, t.outcome, t.verifier_result, t.task_type
               FROM evaluations e
               JOIN transactions t ON e.transaction_id = t.transaction_id
               WHERE e.evaluated_agent_id = ?
               ORDER BY e.created_at""",
            (agent_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_transactions_for(self, agent_id: str) -> list[dict]:
        """あるエージェントが関与した全取引を取得（requester/executor/verifier）"""
        rows = self.conn.execute(
            """SELECT * FROM transactions
               WHERE requester_agent_id = ?
                  OR executor_agent_id = ?
                  OR verifier_agent_id = ?
               ORDER BY started_at""",
            (agent_id, agent_id, agent_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_agent_stats(self, agent_id: str) -> dict:
        """エージェントの基本統計（スコアリングの入力データ）"""
        txs = self.get_transactions_for(agent_id)

        as_executor = [t for t in txs if t["executor_agent_id"] == agent_id]
        as_requester = [t for t in txs if t["requester_agent_id"] == agent_id]

        success_count = sum(
            1 for t in as_executor if t["outcome"] == "success"
        )
        total_executed = len(as_executor)

        verified_pass = sum(
            1 for t in as_executor if t["verifier_result"] == "pass"
        )
        verified_total = sum(
            1 for t in as_executor
            if t["verifier_result"] in ("pass", "fail")
        )

        # Fix #8: is not None で判定（0 を取りうる値に対する truthy 回避）
        durations = [
            t["completed_at"] - t["started_at"]
            for t in as_executor
            if t["completed_at"] is not None and t["started_at"] is not None
        ]

        return {
            "agent_id": agent_id,
            "total_executed": total_executed,
            "total_requested": len(as_requester),
            "success_rate": (
                success_count / total_executed if total_executed else 0.0
            ),
            "verifier_pass_rate": (
                verified_pass / verified_total if verified_total else None
            ),
            "avg_duration_sec": (
                sum(durations) / len(durations) if durations else None
            ),
            "evaluation_count": len(self.get_evaluations_for(agent_id)),
        }

    def check_same_owner(self, agent_a: str, agent_b: str) -> bool:
        """同一オーナー配下かチェック（談合防止用）"""
        a = self.get_agent(agent_a)
        b = self.get_agent(agent_b)
        if not a or not b:
            return False
        if a["owner_id"] and b["owner_id"]:
            return a["owner_id"] == b["owner_id"]
        return False

    def list_all_agents(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM agents ORDER BY registered_at"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["skills"] = json.loads(d["skills"]) if d["skills"] else []
            result.append(d)
        return result

    def stats(self) -> dict:
        agents = self.conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        txs = self.conn.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]
        evals = self.conn.execute(
            "SELECT COUNT(*) FROM evaluations"
        ).fetchone()[0]
        return {"agents": agents, "transactions": txs, "evaluations": evals}


def make_evidence_hash(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def make_transaction_id() -> str:
    return f"tx-{uuid.uuid4().hex[:16]}"
