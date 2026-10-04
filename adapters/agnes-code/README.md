# Agnes Code thin adapter

Validated baseline: Win10 + Agnes Code; host version not exposed.
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

Supersede itself creates the replacement ACTIVE record and marks the old record
SUPERSEDED with reciprocal links. After successful supersede, do not call add
again. Retrieve/inject the replacement in the next session.
