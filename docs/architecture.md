# Architecture

Core: `core/engine.py`，标准库 deterministic 实现。CLI: `cli/__main__.py`，正式 JSON 边界。存储: `memory_store.v1` JSON 容器（records + audit），record schema 冻结为 `memory_record.v1`。JSON Schema 是接口文档，Core 用标准库显式校验输入，不引入验证依赖。

写入流程：确认与敏感 Gate → 类型分类 → 范围内重复/冲突检查 → 明确动作 → record/audit 同一次原子存储写入。读取流程：ACTIVE 与 TTL → project / agent / type 过滤 → lexical relevance / priority / recency → bounded summaries。

ACTIVE 是默认唯一可注入状态。机器是记录范围的一部分，用于防止不同机器上的路径互相替换；检索返回机器字段，V0.1 尚未提供机器查询参数。

安全：所有候选字段整体检查；拒绝时正文不落盘，理由仅为固定代码消息。审计不包含被拒绝的原始候选。已接受正文和补充历史可能包含用户数据，必须由使用者管理本地文件权限。运行数据不进入 Git。仅接受可信调用方确认，不连接任何模型。程序不自动读取聊天、环境变量、凭据或其他 Agent 文件。

持久化只支持串行写入。Adapter 不得直接编辑 storage。扩展类型、存储和 Gate 时应版本化 Contract，不在 V0.1 添加额外服务。

## V0.2 optional architecture

`smart/layer.py` implements the four optional modules and wraps public Core operations. CLI smart commands activate it; old commands remain deterministic V0.1. Observations and relationships live in `<store>.smart.json`, independent of immutable memory_record.v1 semantics. Detailed factors and safety boundaries: [Smart Layer](smart-layer.md).

Promotion uses repeat/time/source/stability evidence only to recommend a change;
trusted explicit confirmation and the Core Gate authorize the final write.
Consolidation joins compatible source clauses without deletion, records all source
IDs/revisions and checks them before promotion and derived recall. Weighted
retrieval is optional: project/agent/machine/type/lifecycle filters apply before
scoring, and bounded injection avoids aggregate/source repetition. Neither layer
requires an LLM. This is a governed fact store, not a chat-history database.

Adapters provide the confirmation boundary and choose when the current task needs
history. They may use the [public contract](build-an-adapter.md), but must not edit
the store directly. The [Hermes Skill Router](hermes-quickstart.md) is a model-mediated
reference integration, not a Core dependency or mandatory host Hook.
