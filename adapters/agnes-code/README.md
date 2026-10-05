# Agnes Code thin adapter

Historical baseline: Win10 + Agnes Code; host version was not exposed.
The recovered host execution used public evaluate/add, retrieve/inject and
explicit supersede with an independent agnes-code-memory.json store.
No original temporary router was persisted; this implementation reproduces that
command protocol. See [quick start](../../docs/agnes-code-quickstart.md).

`adapter.py` is a source-checkout Python reference wrapper, not an AC Core plugin.
`SKILL.md` is an optional on-demand host instruction; installation is manual.
`human_confirmed` must be supplied by trusted user-facing control, never by a
model alone. This wrapper is not a security sandbox for an unrestricted shell.
The trusted caller owns candidate files and serializes write calls.
No Hermes/Codex store sharing, Native Memory access or automatic history sync.

Scoped read compatibility: `context(..., machine='MACHINE', needs_memory=True)`
now requires an explicit machine. The existing wrapper uses public read-only
Smart retrieval for reads, rather than Core retrieval that does not filter machine.
`python -B -m adapters.agnes-code.inspector inject --task "output protocol"
--project Project-AC-Orion --machine Mac-Win10 --budget 500` is the source entry.
Also supports scoped retrieve/smart-retrieve/why/explain; only agnes-code/global
records qualify. Injection summaries are bounded by characters. Explain requires
the ID in the current budgeted selection. Native directories, other agent stores,
aliases and pending migration recovery are refused. Explicitly authorized writes
through the original confirmation methods remain separate from the Inspector.

Install the existing Skill into the host's confirmed `.agnes/skills/agent-memory-os`
directory, substituting the checkout, interpreter and host-root placeholders with
absolute paths. Do not overwrite unknown content or change global configuration.
Native AC Memory and its automatic generation remain host-owned; the adapter does
not read, migrate, synchronize or disable them. Python access audit covers the
Inspector and CLI child, not the whole host. Fresh-host Skill/tool events are
required for E2E; installation presence alone does not prove loading.

Local AC 1.0.68 compatibility acceptance: fictional Gate, scoped Inspector and
Python/CLI native-access audits passed. One new task startup through the installed
local `/agent/start` entry was refused by TLS certificate validation. Real host
Skill loading/E2E is HOST_BLOCKED; no insecure TLS, credential lookup, configuration
change or fallback attempt was used.

Supersede itself creates the replacement ACTIVE record and marks the old record
SUPERSEDED with reciprocal links. After successful supersede, do not call add
again. Retrieve/inject the replacement in the next session.
