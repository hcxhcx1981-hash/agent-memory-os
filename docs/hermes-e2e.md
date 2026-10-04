# Win10 Hermes host E2E — 2026-10-04

Host: Hermes Agent v0.21.5+6750.gea81748 (upstream ea817485).
Program root: <HERMES_HOME>/hermes-agent.
Hermes home: <HERMES_HOME>.
Method: dedicated user Skill, normal `hermes chat -s agent-memory-os-router -t terminal,skills --oneshot -Q` entry. Each of six host invocations exited; none used --resume or --continue. Native memory tool excluded. No Core/config changes.

Synthetic Project-Mercury validation:
- A: explicit assertion → evaluate ACCEPT → add → ACTIVE + CREATE; MEMORY_WRITE_TRIGGERED=true.
- B: fresh process → retrieve/inject → graphite-purple. Injected only old ID.
- C: fresh process arithmetic → 42. Router event count unchanged at 2; no memory query/write.
- D: new theme → evaluate CONFLICT; old remained ACTIVE. Host stopped and requested explicit confirmation.
- Separate explicit E2E confirmation message → supersede → old SUPERSEDED/new ACTIVE with reciprocal IDs, audit CREATE/SUPERSEDE/CREATE.
- E: fresh process → retrieve/inject → obsidian-green only; old excluded.

Old ID: 7acdc613-c023-463a-95c1-b4fcaed1ccb4.
New ID: ea99ddb9-66bb-4a26-bfbf-48e423122600.
These IDs belong only to fictional fixtures, not personal memory.

Live local evidence: storage/hermes-router-events.jsonl (trigger/decision/IDs, no chat text or injection text), storage/hermes-memory.json (fictional records and audit). Both ignored by Git. No full chat logs copied. Native MEMORY.md / USER.md file metadata remained dated before E2E start (UTC 03:02:23 / 03:00:31 versus E2E UTC 05:44 onward); contents not read.

Original ten tests and two compatibility tests validate retained governance and diagnostic filtering. Skill routing is model-mediated, not a forced Hook. Dedicated chat-memory.bat preload is required for the verified route; ordinary chats without preload are not guaranteed. Terminal tools can technically bypass policies, so this is not a security sandbox. Only the default_theme fact pattern was host tested; other natural-language fact shapes remain unverified. Core remains Agent-neutral.
