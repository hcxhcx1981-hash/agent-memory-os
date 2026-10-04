# Hermes V0.2 regression — 2026-10-04

Host version previously verified: v0.21.5+6750.gea81748. Installed dedicated agent-memory-os-router Skill updated; Core, config and other Skills unchanged.

One real normal host chat invocation:
`hermes chat -s agent-memory-os-router -t terminal,skills --oneshot -Q --max-turns 6 --run-budget 90`
No resume/continue. Asked fictional Project-Mercury default theme. Answer: obsidian-green. Actual router smart-retrieve/smart-inject event injected only `ea99ddb9-66bb-4a26-bfbf-48e423122600`; historic graphite-purple excluded. No full chat logs copied, no credentials read. Only the local project diagnostic event was checked.

Offline public-CLI Router regression additionally validates the full V0.1.1 sequence with isolated temporary stores: write ACCEPT → read current ID → changed value CONFLICT and old still ACTIVE → explicit supersede → new ACTIVE only, reciprocal chain. Separate observation test repeats a preference three times and verifies only recommendation, zero ACTIVE records. All calls use public interfaces; no native Hermes memory writes.

This is one live host read regression plus full adapter subprocess regression, not a repeat of every historical host E2E turn. New promotion/consolidation capabilities have deterministic and CLI coverage; model-mediated triggering of those new paths has not been exhaustively host tested. Dedicated Skill preload remains necessary for guaranteed availability.
