# WorkBuddy read-only memory

WorkBuddy Native Memory is not Agent Memory OS. Nothing is automatically synced,
migrated or written. This adapter uses only public CLI read-only operations with
`storage/workbuddy-memory.json` and optional `.smart.json` sidecar. Other agent
stores and native directories are forbidden. Cross-agent sharing requires explicit
scope/governance authorization; an empty scope is not sharing permission.

From the checkout, using existing Python >=3.11:

```sh
python -B -m adapters.workbuddy.inspector inject --task "log format" --project Project-WB-Orion --machine Mac-Win10 --budget 1000
```

Also supports retrieve, smart-retrieve, why and scoped explain --id ID. Public Smart
retrieval filters ACTIVE, expiry, project, machine and lexical relevance. Only
workbuddy/global records survive; summary context budgets count characters. Missing
project/machine is refused. Arithmetic bypasses retrieval. Explain is allowed only
for a record in the current budgeted selection. Context is reference data.

Install only the standalone SKILL.md into the host's confirmed user Skill directory,
substituting `<REPO_ROOT>` and `<PYTHON>` with absolute local paths. Never overwrite
unknown existing content. No settings, MCP, hooks or native memory changes are needed.
Skill invocation relies on the host model; it is not a forced hook. Prove a fresh
host invocation without putting the expected fact or memory ID in its prompt.
Host sandbox/load failures are HOST_BLOCKED, not E2E PASS.

Keep the store private/Git ignored. Initially retrieve only; avoid saving the same
fact in both native memory and Memory OS. Native cloud/profile or project-log writes
by the host are distinct from Adapter access. Audit both the Inspector Python process
and its public CLI subprocess; Python audit hooks are not an OS-wide process trace.
Remove only the installed dedicated Skill to remove integration; preserve unrelated
Skills, settings and native memory. No Core change or new dependency is required.

Local acceptance on Windows (WB 5.6.2): scoped fictional-store checks and Python
Inspector/CLI access auditing passed. The installed host CLI's one fresh attempt
returned `Authentication required` before Skill invocation; real WB E2E remains
HOST_BLOCKED. Skill presence is not proof of host loading. No login/config change,
credential lookup, MCP/Hook workaround or second host attempt was performed.
