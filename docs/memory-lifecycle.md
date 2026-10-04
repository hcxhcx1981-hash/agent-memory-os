# Memory lifecycle

ACCEPT → ACTIVE；精确/近似重复 → DUPLICATE（不新增）；同一 fact_key 变化 → CONFLICT（审计 REJECT，等待人工决定）。

显式 supersede：旧 ACTIVE → SUPERSEDED；新 record → ACTIVE，旧 superseded_by 与新 supersedes 双向链接。禁止替换非 ACTIVE / 已过期记录，禁止跨项目/机器/Agent 范围替换。涉及其他冲突时要求先解决。

显式 supplements：保留原正文的追加候选 → UPDATE；ID 不变，审计保留 before 内容。retire：ACTIVE → RETIRED。TTL 到期：检索立即排除，expire 命令写 EXPIRED 和审计。

REJECTED 是 schema 支持状态，但拒绝候选只落固定原因的审计事件，避免存储敏感正文。evaluate 无副作用，add 再次评价，不能靠先前结果绕过 Gate。无静默覆盖、无自动 supersede。

生命周期结束的记录保留供 get/export 审计，不进入默认 retrieval 或 injection。

## V0.2 observed/candidate lifecycle

Selected preference → OBSERVED; consolidation proposal → CANDIDATE; explicit trusted user confirmation → original Gate → ACTIVE Core record. Repetition only recommends PROMOTE. Inference/sensitive input → redacted REJECTED observation, no original content. Temporary observations expire by TTL and cannot promote permanently. After promotion, Core SUPERSEDED/RETIRED/EXPIRED remains authoritative; smart explain reflects it. Source relationships are retained and revalidated before derived recall. See [Smart Layer](smart-layer.md).
