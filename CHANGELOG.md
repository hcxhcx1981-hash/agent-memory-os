# Changelog

## 0.9.0-rc2

Agnes Code thin public-CLI adapter and on-demand Skill with an independent store,
trusted confirmation, conflict stop and explicit supersede. Supersede creates
the new ACTIVE record itself; no follow-up add. Empty and partial stores normalize
on load; malformed JSON, wrong array types and unknown schemas fail without
overwriting the source. Includes isolated Hermes/Codex stores and the read-only
Codex Inspector delivered since rc1. Schema remains unchanged.

59 tests cover all previous 44 regressions plus empty-store and Agnes Code cases.
Win10 Agnes Code desktop cross-session recall/conflict/confirmed replacement was
confirmed by the user; CLI regressions and fresh-checkout installation are
checked separately. Package spelling: 0.9.0rc2. GitHub Pre-release only; no PyPI.

## 0.9.0-rc1

Release security history review and offline checker; Apache-2.0 LICENSE/NOTICE
and dependency review; portable installation and Hermes/generic adapter guides;
fictional executable Quick Start/demo; offline Python 3.11–3.14 CI; isolated
packaging checks. No new Core capability or schema changes. No publication.

Package metadata uses the PEP 440 spelling `0.9.0rc1`. Version advanced only
after preflight clean-clone installation, offline demos, 32 tests and all six
CI jobs passed. Repository remains PRIVATE.

## 0.2.0

Optional deterministic Semantic Judge, observed/candidate lifecycle with confirmed promotion, lossless consolidation with retained source relationships, scoped weighted retrieval, explain/why CLI. Hermes router uses smart layer while preserving V0.1.1 syntax. Core schema unchanged; independent smart_state.v1 and memory_relationship.v1 contracts. No runtime dependencies added.

## 0.1.0

Deterministic Gate, five memory types, versioned JSON schema, scoped deduplication/conflicts, explicit supplement/supersede/retire/expire, lexical retrieval, bounded injection, audit trail, UTF-8 CLI and Hermes reference adapter. No runtime dependencies or model calls.
