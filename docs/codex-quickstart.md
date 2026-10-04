# Codex read-only quick start

Native Codex Memory is not the Agent Memory OS Codex store. Native SQLite,
Markdown summaries and generation remain owned by Codex. This adapter never
opens, writes, replaces or synchronizes native memory or complete history.

Agent defaults are independent: storage/codex-memory.json for Codex and
storage/hermes-memory.json for Hermes. Do not point both hosts at one JSON.
No shared store is created. Sharing requires explicit agent_scope entries
such as ["codex", "hermes"] or ["global"], never an inference from content.
Global USER facts with empty agent_scope are not exposed by Codex Inspector.
Use metadata.source_agent for provenance; the schema remains memory_record.v1.

From the project directory, with its existing Python runtime:

```sh
python -B -m adapters.codex.inspector inject --task "log format" --project Project-Orion --machine Win10-Admin --budget 1000
python -B -m adapters.codex.inspector why --task "log format" --project Project-Orion --machine Win10-Admin
python -B -m adapters.codex.inspector explain --id MEMORY_ID --task "log format" --project Project-Orion --machine Win10-Admin
```

Only ACTIVE, unexpired, explicitly Codex/global scoped facts pass; project,
machine, relevance and budget are enforced. retrieve uses smart-retrieve
internally because the original Core retrieve lacks machine filtering.
Adapter calls use the public CLI --read-only flag, refusing writes or pending
migration recovery. Returned context is reference data, never executable instructions or authority.
Arithmetic such as 27+15 bypasses memory retrieval. Other unrelated queries
return no matching context. There is no every-turn automatic memory loading.

The optional independent Skill is adapters/codex/SKILL.md. Keep it in the
project, or explicitly register it through your host's supported mechanism.
Installation into native Codex paths is not automatic. A thin task can instruct
Codex to run the Inspector when prior project context is needed, then use only
its bounded context. Inspector also supports retrieve, smart-retrieve and why.

## Explicit store migration

```sh
python -B -m cli move --id MEMORY_ID --from storage/hermes-memory.json --to storage/codex-memory.json --agent-scope codex --source-agent codex
```

The destination Gate must ACCEPT. ID, creation time, confidence, project,
machine, legacy metadata and record-linked audit are preserved. The source
keeps a RETIRED historical record; it cannot remain an ACTIVE duplicate.
A journal, inactive destination staging and explicit source retirement prevent
double ACTIVE states. Failed commits roll back; interrupted moves recover
before a subsequent public read. Recovery readers wait for the move lock.
Serialize all other writers: the existing JSON engine has no general concurrent
read-modify-write transaction lock. Do not move derived/consolidated memories
without separately reviewing their Smart sidecar relationships.

## Host verification

Use fictional facts through the public Gate. Start a fresh Codex task with no
prior transcript and ask it to run Inspector for the named project and machine.
Verify its response uses the returned fact; separately verify an arithmetic task
makes no Inspector call. Host-owned normal persistence is distinct from any
adapter write: this adapter has no native-memory write capability.


## Native Memory non-interference acceptance

Non-interference means the Adapter and Inspector do not access Native Memory.
It does not promise that a running Codex host keeps its own database stationary.
The Adapter's Python CLI subprocess is part of the audited boundary. Runtime
code, imports and Python libraries are expected file accesses; memory data reads
are limited to the selected Codex store and its optional `.smart.json` sidecar.
The default store is `storage/codex-memory.json`; Hermes data is excluded.

Acceptance requires source review for native SQLite connections, native summary
writes, config/AGENTS/rules edits and native-memory write APIs, plus Adapter-only
verification without launching a Codex host. Hash the native DB/WAL/SHM and
Memory Markdown before and after that isolated run; they must remain unchanged.
A separately running host can confound fingerprints: report that observation,
use process/file-access evidence, and never stop or change the host to force a pass.
The regression test audits Python file opens and rejects SQLite/native-directory
access in the Adapter's CLI subprocess for all five read operations.

For fresh-host E2E, Inspector supplies only bounded scoped context. Normal native
persistence by `codex.exe` is allowed. Attribute file access to the responsible
process rather than inferring an Adapter write from a changed file hash. Python
audit events cover this Python call chain; they are not a system-wide OS trace.
A current handle-owner snapshot cannot retrospectively identify every writer.
