# CHANGELOG

All notable changes to this project will be documented in this file.

## v0.1.0-phase0

Initial public release of ARP as a ledger-first trust substrate prototype for the A2A ecosystem.

### Added
- Append-only transaction ledger for agent-to-agent interactions
- Transaction-bound evaluation recording tied to actual interactions
- Deterministic score derivation from ledger data
- Same-owner collusion decay for mutual evaluations
- A2A extension-compatible extended agent card
- Self-contained end-to-end demo using FastAPI TestClient
- Pytest-based test suite covering core guardrails and scoring behavior
- `docs/SEMANTICS.md`
- `docs/THREAT_MODEL.md`
- `ROADMAP.md`

### Security / integrity guardrails
- Self-evaluation rejected at the ledger level
- Self-transaction rejected at the ledger level
- Third-party drive-by evaluations blocked
- Duplicate evaluations blocked
- Unregistered verifier rejected
- Empty evaluation rejected
- Referential integrity enforced with foreign keys

### Clarified
- The ledger is the primary artifact; scores are derived secondary artifacts
- The prototype is ledger-first, append-only, transaction-bound, and reproducible
- Trust data is exposed through the A2A `extensions` mechanism used by the prototype
- PageRank-style evaluator weighting is planned for v0.2
- A provider-neutral minimal trust attestation surface is being discussed separately and is not implemented here

### Not included
- Cryptographic attestations or portable signature-based verification
- Provider-neutral minimal trust attestation surface implementation
- Graph-based trust composition
- Delegation policy or routing logic
- Real HTTP transport demo between separate running agents

### Current positioning
ARP is a Phase 0 / pre-standard trust substrate prototype. It is intended to show a hard ledger-first base for trust-relevant records before higher-layer trust composition, routing, or provider-neutral attestation standardization.
