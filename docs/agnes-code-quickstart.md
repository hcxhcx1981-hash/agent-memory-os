# Agnes Code quick start

Win10 + Agnes Code is the validated baseline; host version not exposed.
Use `<AGENT_MEMORY_OS_ROOT>` for this checkout, `<AGNES_CODE_ROOT>` for the host,
and `<USER>` where a user placeholder is needed. Do not change host Core or
Native Memory. [Thin router](../adapters/agnes-code/README.md) and
[Skill](../adapters/agnes-code/SKILL.md) use public CLI only.

After `pip install .`, trusted user-facing control can execute:

```sh
memory --store "<AGENT_MEMORY_OS_ROOT>/storage/agnes-code-memory.json" evaluate --candidate nova-write.json
memory --store "<AGENT_MEMORY_OS_ROOT>/storage/agnes-code-memory.json" add --candidate nova-write.json
memory --store "<AGENT_MEMORY_OS_ROOT>/storage/agnes-code-memory.json" retrieve "output format" --project Project-Nova --agent agnes-code
memory --store "<AGENT_MEMORY_OS_ROOT>/storage/agnes-code-memory.json" inject "output format" --project Project-Nova --agent agnes-code --budget 500
```

A fictional candidate, after the human confirms the exact fact:

```json
{"content":"Project-Nova output format is dense-markdown","type":"PROJECT","project":"Project-Nova","agent_scope":["agnes-code"],"confirmed":true,"source_type":"user","metadata":{"source_agent":"agnes-code","fact_key":"output_format"}}
```

Call add only if evaluate returns ACCEPT. In a fresh host session run the same
scoped retrieve/inject, then answer from returned context. To change the fact,
create nova-change.json with compact-json and the same scope/fact_key; evaluate
must return CONFLICT. Stop and obtain explicit replacement approval before:

```sh
memory --store "<AGENT_MEMORY_OS_ROOT>/storage/agnes-code-memory.json" supersede OLD_ID --candidate nova-change.json --reason "User confirmed format replacement"
```

A new session must inject only compact-json, never the superseded fact. Skip
unrelated tasks; do not retrieve the full store every turn. Candidate files are
trusted caller-owned inputs; neither a JSON flag nor a model's recommendation
creates human approval. The reference wrapper requires separate human_confirmed.
Original retrieve/inject filter project and agent, not machine; use the public
smart commands when machine filtering is required. Never share this store with
Hermes/Codex. An absent store or {} is normalized on load; writes initialize the
standard structure. Malformed JSON or wrong records/audit types fail without
overwriting the original file. Native host persistence remains host-owned.

Supersede itself creates the replacement ACTIVE record and marks the old record
SUPERSEDED with reciprocal links. After successful supersede, do not call add
again. Retrieve/inject the replacement in the next session.
