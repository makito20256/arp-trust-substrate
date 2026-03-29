# SEMANTICS

## Purpose

ARP is a ledger-first trust substrate prototype.

Its job is to record trust-relevant events in a form that is:

- append-only,
- transaction-bound,
- reproducible,
- and suitable for deterministic re-derivation of judgments.

It is **not** a full trust standard, a cryptographic attestation layer, or a delegation policy engine.

## Ledger-first

In ARP, the ledger is the primary artifact.

Scores, search results, and Agent Card extensions are all derived views over ledger records. If a trust signal cannot be traced back to a ledger entry, it does not exist within ARP's semantic core.

This means:

- no reputation without recorded interactions,
- no evaluation without a transaction,
- no derived score without replaying ledger data.

## Transaction-bound evaluation

Evaluations are only meaningful when bound to an actual transaction.

ARP therefore requires that an evaluation reference a previously recorded transaction, and only parties to that transaction may evaluate it:

- requester,
- executor,
- or verifier.

This excludes drive-by ratings and ungrounded peer review from the semantic core.

## Deterministic recomputation

Derived judgments must be reproducible from the same ledger.

Given the same ledger contents, ARP should always derive the same score outputs. This is a core semantic property, not just an implementation detail.

Deterministic recomputation matters because it makes trust-relevant outputs:

- reviewable,
- testable,
- auditable,
- and less vulnerable to hidden state.

## Scores are secondary artifacts

ARP does expose derived scores, but those scores are not the primary trust object.

The primary object is the recorded history itself:

- who interacted,
- when,
- with what task type,
- with what outcome,
- with what evidence hash,
- and with what evaluation or verification outcome.

Scores exist to summarize that history, not replace it.

## Boundary with the broader A2A trust discussion

ARP is intentionally narrower than the provider-neutral trust attestation surface currently being discussed in the A2A community.

ARP today provides:

- immutable transaction recording,
- transaction-bound evaluations,
- deterministic derived judgments,
- and an A2A-extension-compatible way to expose those derived judgments.

ARP does **not** yet define:

- a minimal provider-neutral attestation schema,
- portable cryptographic attestations,
- cross-provider trust composition,
- or delegation-time trust policy.

## Summary

ARP should be read as a hard substrate prototype:

- ledger first,
- transaction bound,
- deterministic,
- auditable,
- and intentionally limited in semantic scope.

That limitation is a feature, not a gap.
