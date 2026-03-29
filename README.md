# Agent Reputation Protocol (ARP)

A ledger-first trust substrate prototype for the A2A ecosystem.

## What this is

ARP is a prototype that records agent-to-agent interactions as immutable ledger entries, then derives trust-relevant judgments from those records deterministically.

The core premise is simple: **what happened between agents should be recorded in a form that is append-only, transaction-bound, and reproducible** before any scoring, ranking, or trust composition is applied on top.

This is not primarily a reputation scoring service. Scores exist in the prototype, but they are secondary to the ledger itself. The primary artifact is the ledger: a reproducible history of which agent did what, for whom, when, with what outcome, and whether a third party verified it.

## Design principles

**Ledger-first.** All trust signals are derived from the transaction ledger. There is no score without a record. The same ledger always produces the same derived scores (deterministic recomputation).

**Transaction-bound evidence.** Evaluations are only accepted from parties to an actual transaction (requester, executor, or verifier). No drive-by reviews. No ratings without interaction.

**Anti-collusion by default.** Same-owner mutual evaluations are decayed to 0.3× weight. Self-evaluation and self-transaction are rejected at the ledger level. Duplicate evaluations are blocked by a UNIQUE constraint.

**A2A extension compatible.** Trust data is currently exposed through the A2A `extensions` mechanism used by the prototype. No modification to the core A2A spec is required.

> **Current status:** This is a Phase 0 prototype. Scoring uses simple weighted averages. PageRank-style evaluator weighting is planned for v0.2. A provider-neutral minimal trust attestation surface is being discussed separately in the A2A community — ARP does not claim to implement that standard.

## Structure

```text
agent-reputation-protocol/
├── ledger/transaction_ledger.py   # Core: append-only immutable ledger
├── scoring/engine.py              # Deterministic score derivation from ledger
├── api/service.py                 # FastAPI HTTP layer + Extended Agent Card
├── demo/run_demo.py               # Self-contained end-to-end demo (TestClient)
├── docs/SEMANTICS.md              # Semantic boundary and substrate meaning
├── docs/THREAT_MODEL.md           # Threats, defenses, and non-goals
├── ROADMAP.md                     # Versioned roadmap
└── tests/                         # Pytest-based checks for current guarantees
```

## Quick start

```bash
pip install fastapi uvicorn httpx pytest

cd agent-reputation-protocol
python demo/run_demo.py        # In-process demo, no network required

python api/service.py          # Run as HTTP server
pytest -q                      # Run tests
```

## API

| Endpoint | Method | Description |
|---|---|---|
| `/agents/register` | POST | Register an agent |
| `/transactions` | POST | Record a transaction to the ledger |
| `/evaluations` | POST | Record a transaction-bound evaluation |
| `/reputation/{agent_id}` | GET | Derive a reputation score from the ledger |
| `/search` | GET | Search agents by derived reputation |
| `/agent-card/{agent_id}` | GET | Extended Agent Card (A2A extension) |
| `/transactions/{agent_id}` | GET | Transaction history for an agent |
| `/stats` | GET | Ledger statistics |

## Anti-gaming measures

| Attack pattern | Defense |
|---|---|
| Self-evaluation | Rejected at ledger level |
| Self-transaction | Rejected at ledger level |
| Third-party drive-by rating | Only transaction parties can evaluate |
| Duplicate evaluation | UNIQUE constraint on (transaction, evaluator, evaluated) |
| Empty evaluation | All-null scores rejected |
| Same-owner collusion | Mutual evaluation weight decayed to 0.3× |
| Unregistered verifier | FK constraint + application-level check |
| Referential integrity | `PRAGMA foreign_keys = ON` |

## What this does not do (yet)

- **No PageRank or graph-based scoring.** v0 uses flat weighted averages. Evaluator-weighted scoring is planned for v0.2.
- **No cryptographic attestations.** The ledger relies on application-level integrity, not Ed25519 signatures. Portable verifiability is a direction, not a current feature.
- **No provider-neutral attestation surface.** A minimal trust extension schema is under active discussion in the A2A community. ARP does not implement it yet.
- **No real HTTP transport demo.** The current demo uses FastAPI TestClient (in-process). A localhost HTTP demo with actual A2A card fetch and message send is planned.
- **No delegation policy engine.** ARP records and derives trust-relevant judgments. It does not decide how agents should route or delegate work.

## License

Apache 2.0
