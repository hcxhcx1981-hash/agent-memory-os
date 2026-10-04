# Optional Smart Memory Layer v0.2

四个模块位于 `smart/layer.py`；可通过 CLI 调用，不依赖 LLM。SemanticJudge 使用有限的句式、实体关系（缩写定义、项目路径）、时间和不确定性识别提出评分；它是确定性基线，不是通用自然语言理解器。Judge / SemanticRetriever Protocol 只预留未来接口，没有外部 API 实现。

## Judge 与可信写入

返回 should_remember、memory_type、stability_score、future_value_score、confidence、reason、suggested_fact_key、suggested_scope、suggested_ttl、risk_flags。语义判断只是建议；不确定推测、模型来源、敏感内容、情绪和原始日志不能进入基础记忆。可选 Judge 无法抬高 baseline 稳定性或绕过其拒绝，不能提供事实确认权限。

`observe` 默认只保存筛选后的 OBSERVED。`--user-confirmed` 必须对应真实用户对该具体事实的明确长期确认，且候选 confirmed=true；满足稳定性和来源要求才调用 promote → 原 Core evaluate → add。Gate 校验探针用 confirmed=true 只检查格式/敏感/冲突，不执行写入。正式 add 需要可信调用方的明确确认。智能层额外识别常见直接否定，避免原 Core 高相似去重掩盖这种冲突；不改变 Core。

## Promotion

默认三次同范围、同内容偏好观察才能推荐；观察次数可以发生在短时间内，因为只是建议，仍须用户确认。记录 repeat_count、首末时间、time_span、source_quality、stability、explicit_user_confirmation、conflict_state。evidence_score = 0.4 repetition + 0.2 elapsed-days (cap 1) + 0.2 source-quality + 0.2 stability；推荐至少 0.72、重复次数≥3、质量≥0.8、稳定性≥0.7且无冲突。用户直接长期确认可省去重复要求，但不能绕过来源、稳定性或 Core Gate。

单次临时表达为 EPISODIC OBSERVED，默认七天 TTL。临时观察不会永久晋升。多次重复不能升级模型推测。import/system 基线质量为 0.6，仅观察不能晋升，需可信用户重新确认来源。冲突或 UPDATE 建议不会自动执行；supersede 仍是明确的单独生命周期动作。

## Consolidation

`consolidate ID...` 只创建 CANDIDATE。所有来源必须 ACTIVE、未过期、同 project/machine/agent/type；重复 ID、相同 fact_key 的不同值、显式 conflicts_with 或可识别的直接否定/相反状态被拒绝。候选是原正文的无损分号连接，不改写、不抽象出新事实。保存 source IDs 和 SHA-256 来源版本摘要；用户确认 promote 时再次检查来源版本，原记录保持 retained，另保存 memory_relationship.v1。

已晋升归纳内容的来源若后来 UPDATE/退役/被替换，smart retrieval 将其排除并解释 derived_source_changed，防止旧事实通过归纳重新进入上下文。不会自动修改归纳 ACTIVE record，也不删除源记录。注入避免同时使用源与聚合关系产生明显重复。

没有通用语义冲突证明：无法识别的隐含矛盾必须由用户审阅、或为互斥事实提供同一 fact_key。V0.2 无模型压缩，超 2000 字的合并会拒绝。

## Context retrieval 与解释

先严格过滤 ACTIVE/TTL、project、agent、machine、type，再对任务词与中文二元片段评分。任务可推断明确出现的 Win10/Win11；project/agent 应由调用方明确传入。不指定 project 排除项目专属记录；不指定 machine 排除机器专属记录。不自动从猜测选项目。

加权因素包含 task relevance (≤50)、project (10)、agent (5)、machine (10)、type (1–5)、priority (≤10)、recency (≤5)、confidence (≤5)、stability (≤5)、有效归纳 relationship (3)、ACTIVE (1)。范围和任务相关性是先决过滤，不能靠高 priority 越过。`why` 返回 score、matched_factors、matched_terms、excluded_reason；smart-inject 在字符预算内装入完整摘要。

`explain ID` 支持观察 ID、拒绝 ID、Core ID，返回判断、晋升因素、原因、审计及关系。`why TASK` 是本次查询诊断；不会写完整查询历史。拒绝记录只有生成 ID、REJECTED、固定原因和时间，不保留敏感正文。OBSERVED/CANDIDATE 过期及晋升后状态以有效生命周期解释，Core 记录状态是最终权威。

## 兼容与存储

memory_record.v1 / memory_store.v1 完全不变。新文件 `<store>.smart.json` 使用 smart_state.v1，包含 observations、relationships、audit。关系 contract 为 memory_relationship.v1。旧文件无需迁移；没有 sidecar 时智能层视为无观察/关系。旧 add/evaluate/search/retrieve/inject 保持 V0.1 行为；只使用 smart-* 或 observe/promote 才启用新功能。

Core 与 sidecar 各自原子写入，但没有跨文件事务。单用户串行写入；应备份两个文件，失败后通过 explain/get/audit 检查，重复执行 Core Gate 不会自动覆盖旧记录。删除文件和后台全量同步均不属于本版本。
