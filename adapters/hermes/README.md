# Hermes reference adapter

Current user installation and removal instructions:
[Hermes Quick Start](../../docs/hermes-quickstart.md).

Verified Windows host: v0.21.5+6750.gea81748. The independent Skill Router
uses the public CLI and an independent store. It does not change native Memory.
Routing depends on the model following the Skill, not a mandatory Hook.

`ROUTER_SKILL.md` is the current template: replace its Python/root placeholders
locally before installation. Keep that generated file private. `SKILL.md` is
the original minimal contract example, not the current host installation template.
`chat-memory.bat` uses the dedicated normal chat entry with terminal and skills
tools. Keep a source checkout for the router; wheel installation alone does not
configure Hermes.

The original Python adapter remains a minimal evaluate/add/inject example:

```python
from pathlib import Path
from adapters.hermes.adapter import HermesAdapter
root = Path.cwd()
adapter = HermesAdapter(root, root / 'storage/hermes-example.json')
result = adapter.remember(root / 'examples/theme.json')
context = adapter.context('default_theme', 'Project-Mercury')
```

V0.2 router write/read/supersede are compatible with the original routes.
Selected observe stages a preference; repeat evidence only recommends promotion.
Formal promote and supersede require explicit human confirmation. Read uses
scoped weighted retrieval and bounded reference context. No blanket per-message
queries, automatic chat import or native Memory dual writes.

Local trace stores minimal decision/ID/recommendation evidence, not full messages
or injected context. Stores and generated Skill files are Git-ignored.
[Host evidence](../../docs/hermes-promotion-consolidation-e2e.md) and
[generic contract](../../docs/build-an-adapter.md) describe the verified boundaries.
