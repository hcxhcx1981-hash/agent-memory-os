# Build an adapter

Core is agent-neutral and does not require an LLM. A read-only Codex Adapter / Inspector is included.
WorkBuddy and DHAF adapters are not implemented.

WRITE: selected candidate → evaluate → add only on ACCEPT. Add re-evaluates.
Stop on CONFLICT/REJECT/UPDATE/DUPLICATE rather than inventing permission.
Use stable `metadata.fact_key` for changeable properties.

READ: relevant task and scope → retrieve or smart-retrieve/why → bounded
inject or smart-inject. Pass returned context as reference data. Do not query
all memory every turn, save every message or import complete chat histories.

## Minimal installed-package Python adapter

```python
import json
import subprocess
from pathlib import Path

class Adapter:
    def __init__(self, store, agent):
        self.store = str(Path(store).resolve())
        self.agent = agent

    def call(self, *args):
        result = subprocess.run(
            ['memory', '--store', self.store, *args],
            check=True, capture_output=True, text=True, encoding='utf-8')
        return json.loads(result.stdout)

    def write(self, candidate_file, *, human_confirmed):
        # Trusted host control logic establishes this, never the model itself.
        if human_confirmed is not True:
            return {'decision': 'NEEDS_CONFIRMATION'}
        path = Path(candidate_file).resolve()
        candidate = json.loads(path.read_text(encoding='utf-8'))
        if candidate.get('confirmed') is not True:
            return {'decision': 'NEEDS_CONFIRMATION'}
        verdict = self.call('evaluate', '--candidate', str(path))
        if verdict['decision'] == 'ACCEPT':
            return self.call('add', '--candidate', str(path))
        return verdict

    def context(self, task, project):
        scope = ['--project', project, '--agent', self.agent]
        if not self.call('retrieve', task, *scope):
            return {'context': '', 'memory_ids': []}
        return self.call('inject', task, *scope, '--budget', '500')
```

For source execution use `[sys.executable, '-m', 'cli']` with cwd set to the
checkout. The trusted wrapper must control write access, own the candidate file
while calls run, establish confirmation and serialize writers. A model-controlled
`confirmed=true` argument is not a permission boundary. The example assumes
trusted file ownership; it is not a complete security sandbox.

## Lifecycle and explanations

- `observe --candidate FILE` stages selected facts; `promotion-candidates` returns
  repeat/time/source/stability evidence. `promote ID --user-confirmed` requires
  trusted human approval, never an assistant's recommendation alone.
- `consolidate ID...` proposes unchanged clauses with source IDs. Explain them,
  obtain confirmation, then promote. Originals remain; changed source revisions
  invalidate proposals and derived recall. Known contradictions block proposals.
- CONFLICT stops writes. Get evidence, obtain separate approval, then
  `supersede OLD_ID --candidate FILE --reason REASON`.
- `retire ID --reason REASON` removes a fact from normal recall but retains
  history; `expire` records TTL transitions. `get`/`export` expose history.
- `explain ID` provides state/audit/source trace. `why TASK` returns retrieval
  scores and exclusions. smart-inject avoids aggregate/source duplication.

Always select the same `--store` before the command. Never edit store JSON
directly. Log minimal IDs/decisions, not message bodies. Budget counts characters,
not tokens. See [contract](adapter-contract.md), [lifecycle](memory-lifecycle.md),
and [architecture](architecture.md).


## Independent stores and Codex Inspector

Agent defaults use separate Hermes and Codex stores. Cross-agent sharing must be
explicit. The read-only Codex Inspector retrieves project/machine/agent scoped
context on demand; native Codex memory remains separate. Public `move` preserves
IDs and provenance with Gate, journal recovery and RETIRED source history.
See [Codex quick start](codex-quickstart.md).

Native Memory non-interference means no Adapter access to native data or rules;
it does not require a running Codex host database to remain unchanged. See
[codex-quickstart.md](codex-quickstart.md#native-memory-non-interference-acceptance)
for isolated fingerprints, subprocess access auditing and host attribution limits.

## Agnes Code

The [Agnes Code thin router](../adapters/agnes-code/README.md) reproduces the
validated public CLI evaluate/add, retrieve/inject and explicit supersede chain.
Use a separate agnes-code store and trusted user confirmation. No host Core or
Native Memory integration is installed automatically.
