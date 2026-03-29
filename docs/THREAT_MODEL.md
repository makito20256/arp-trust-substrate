# THREAT MODEL

## Purpose

This document separates what ARP currently defends against from what remains future work.

ARP is a Phase 0 ledger-first trust substrate prototype. Its threat model is therefore intentionally narrow: protect the integrity of transaction-bound evaluation and make derived judgments reproducible.

## Current defenses

| Threat | Current defense | Layer |
|---|---|---|
| Self-evaluation | Rejected during evaluation recording | Ledger |
| Self-transaction | Rejected during transaction recording | Ledger |
| Third-party drive-by rating | Only transaction parties may evaluate | Ledger |
| Duplicate evaluation | UNIQUE constraint on `(transaction_id, evaluator_agent_id, evaluated_agent_id)` | Ledger |
| Empty evaluation | All-null score submissions are rejected | Ledger |
| Unregistered verifier | Foreign key constraint + application-level check | Ledger |
| Same-owner collusion | Mutual evaluations are down-weighted to 0.3× | Scoring |
| Hidden score drift | Scores are recomputed deterministically from ledger contents | Scoring |

## What these defenses are meant to guarantee

ARP currently aims to guarantee the following:

1. **No ungrounded evaluation.**
   Every evaluation must be tied to a recorded transaction.

2. **No self-boosting through trivial self-reference.**
   Self-transaction and self-evaluation are blocked at the ledger level.

3. **No duplicate score inflation through repeated submissions.**
   Duplicate evaluations for the same transaction/evaluator/evaluated tuple are rejected.

4. **No same-owner evaluation should carry full weight by default.**
   Same-owner relationships are treated as a collusion risk and decayed in scoring.

5. **Derived judgments remain reproducible.**
   Scores are functions of ledger state, not hidden mutable state.

## What ARP does not yet defend against

These remain explicitly out of scope for the current prototype:

| Threat | Status | Why |
|---|---|---|
| Sybil attacks across many independently registered agents | Future | Requires identity / registration hardening beyond current substrate |
| Trust-building then exploit | Future | Requires temporal weighting, scoped trust decay, or higher-layer controls |
| Capability inflation | Future | Requires finer-grained capability-scoped trust semantics |
| Portable attestation forgery resistance | Future | No cryptographic attestation layer yet |
| Cross-provider trust calibration | Future | ARP is not yet a provider-neutral attestation surface |
| Delegation-time trust policy | Future | ARP records and derives; it does not decide delegation |

## Layer split

### Ledger-level defenses
These operate at recording time and constrain what may enter the substrate.

- self-transaction rejection
- self-evaluation rejection
- party-of-transaction requirement
- duplicate evaluation blocking
- empty evaluation rejection
- verifier registration checks
- foreign key integrity

### Scoring-level defenses
These operate after recording and affect derived judgments.

- same-owner decay
- deterministic recomputation
- confidence based on data sufficiency

## Non-goals

ARP is not currently trying to be:

- a complete anti-Sybil system,
- a cryptographic attestation network,
- a graph-based trust engine,
- or a delegation control layer.

## Summary

ARP's current security posture is best understood as:

- **hardening the substrate**,
- **binding trust signals to real interactions**,
- and **preventing obvious local abuse**.

Broader trust composition and adaptive control are future layers, not current guarantees.
