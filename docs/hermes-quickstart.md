# Hermes Quick Start

Verified host: **v0.21.5+6750.gea81748** on Windows, using fictional fixtures.
Historical independent-session evidence:
[V0.1](hermes-e2e.md), [V0.2 regression](hermes-v02-regression.md),
[promotion/consolidation](hermes-promotion-consolidation-e2e.md).
This verifies that host version, not all versions or models.

Local compatibility acceptance also passed on Windows host
`0.21.5+7249.g7157422`, using its restored default `agnes / agnes-3.0-flash`.
A fresh dedicated `chat -s agent-memory-os-router -t terminal,skills` session
returned the fictional Project-H-Orion convention through a real terminal Router
result, with reference-only context and the expected ID; the prompt had no answer.

The reference adapter uses a **dedicated Skill Router** calling the public CLI.
Core JSON, optional Smart sidecar and diagnostics are independent of Hermes
native Memory. There is no migration or native file edit. Routing relies on
the host model executing Skill instructions; it is not a mandatory Hook. If
Skill loading changes, inspect the host read-only before adding compatibility.

## Install the dedicated Skill

Follow [project installation](installation.md) and keep the source checkout:
a bare wheel is not a complete Skill installation. Check `hermes --version`
and `hermes chat --help` to confirm the normal entry. Determine the actual host
home and user Skill directory from your installation. The verified Windows
layout used `%LOCALAPPDATA%/hermes`; do not assume yours does.

From the checkout, prepare a local Skill in PowerShell:

```powershell
$memoryRoot = (Get-Location).Path.Replace('\', '/')
$memoryPython = (Get-Command python).Source.Replace('\', '/')
$skillText = Get-Content adapters/hermes/ROUTER_SKILL.md -Raw
$skillText = $skillText.Replace('<AGENT_MEMORY_OS_ROOT>', $memoryRoot)
$skillText = $skillText.Replace('<MEMORY_OS_PYTHON>', '"' + $memoryPython + '"')
New-Item -ItemType Directory -Force work/hermes-skill | Out-Null
[IO.File]::WriteAllText((Join-Path (Get-Location) 'work/hermes-skill/SKILL.md'), $skillText, [Text.UTF8Encoding]::new($false))
```

For a venv, select its Python executable instead. The verified host terminal
uses shell-style calls; if yours uses PowerShell, prefix quoted executable
calls in the generated Skill with `&`. Confirm the actual terminal mechanism.

Copy the generated file to the **confirmed** host home at
`<HERMES_HOME>/skills/agent-memory-os-router/SKILL.md`, creating only that dedicated
Skill directory. If it exists, review before replacing it. On Linux/macOS,
replace the same template's `<AGENT_MEMORY_OS_ROOT>` and `<MEMORY_OS_PYTHON>` with
your checkout and Python executable; host Skill loading needs separate verification.
Generated local files contain your paths and must stay private. No credentials,
config or native memory need to be read.

## Entry and independent store

```sh
hermes chat -s agent-memory-os-router -t terminal,skills
```

Windows can also run `adapters/hermes/chat-memory.bat` when `hermes` is on PATH.
This dedicated tool list excludes native memory. Other normal entrypoints may
use native Memory separately; do not save these same facts through both systems.

Router `read` requires explicit project and machine. Read calls use public CLI
`--read-only`; only explicitly hermes/global scoped records are injected. Native
paths, other agents' stores, aliases and pending migration recovery are refused.
Arithmetic bypasses retrieval and diagnostics. Router writes set hermes scope and
source provenance. Existing unscoped records are not automatically migrated.
Read diagnostics may append to the independent trace but do not modify the store.
Python Router/CLI access audits cover this boundary, not host-owned persistence.

Default store: `<AGENT_MEMORY_OS_ROOT>/storage/hermes-memory.json`.
Sidecar: `hermes-memory.json.smart.json`; trace:
`storage/hermes-router-events.jsonl`. Keep these private and user-writable.
A custom location must be supplied consistently using router `--store` and
`--trace`, and every direct CLI command in the generated Skill must also use it.

## Prove cross-session behavior

1. State: “以后测试项目 Project-Mercury 的默认主题是 graphite-purple。”
   Check MEMORY_WRITE_TRIGGERED, MEMORY_DECISION=ACCEPT and MEMORY_ID. Verify
   ACTIVE through formal get and CREATE through export/explain.
2. Exit. Start a fresh entry without resume/continue. Ask “Project-Mercury
   默认主题是什么？” Require graphite-purple **and**
   MEMORY_RETRIEVAL_TRIGGERED with the expected INJECTED_MEMORY_IDS. A correct
   answer alone is not proof of retrieval.
3. A fresh arithmetic session “15 + 27 等于多少？” should answer 42 without a
   router call or new trace event; unrelated memory must not enter context.
4. Change to obsidian-green. Require CONFLICT and a stop. Only a subsequent
   explicit human approval permits supersede. Verify old=SUPERSEDED, new=ACTIVE,
   reciprocal links and SUPERSEDE audit.
5. A fresh recall must inject only obsidian-green; get/export retain history.

Diagnostics contain decisions, IDs and promotion factors, not complete messages
or injected context. Inspect locally through public commands from the checkout:

```sh
python -m cli --store storage/hermes-memory.json get MEMORY_ID
python -m cli --store storage/hermes-memory.json explain OBSERVATION_OR_MEMORY_ID
python -m cli --store storage/hermes-memory.json why default_theme --project Project-Mercury --agent hermes
```

Selected unconfirmed observations can recommend promotion after repeats; human
approval is still required. Consolidation proposals list all source IDs and
unchanged clauses; confirmation precedes promote. A model cannot self-confirm.
Known natural-language contradiction detection is limited.

## Uninstall and delete data

Stop writers. Remove only the dedicated
`<HERMES_HOME>/skills/agent-memory-os-router` directory and stop using its `-s`
flag. This removes integration, not data. Back up Core and sidecar together if
needed. For complete Memory OS data removal, manually delete only its selected
Core file, matching sidecar, router trace, demo stores and backups. Leave native
Hermes MEMORY.md/USER.md and all unrelated Skills untouched. See
[backup/removal details](installation.md).
