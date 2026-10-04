# Adapter Contract v1

1. Adapter 把已确认、单条、筛选后的事实转换成候选 JSON 文件：content、confirmed、source_type 必填约定；推荐 type、project、agent_scope 和 metadata.fact_key。
2. 使用正式 CLI evaluate，只有 ACCEPT 才提交 add；add 必须重新 Gate。UPDATE/CONFLICT 必须显式由调用方确认并调用对应公共命令，禁止模型默默替换。
3. 检索调用 retrieve；最小上下文调用 inject，传 task、project、agent 和字符 budget。只使用返回的 context 与 ID，不读取或修改 Core 数据文件。
4. 公共入口：`python -m cli --store ABSOLUTE_PATH COMMAND ...`，成功输出 UTF-8 JSON；参数或操作错误返回退出码 2，Gate 拒绝是 JSON decision 而不是进程失败。
5. Memory record schema `memory_record.v1`，见 schemas；日期为 ISO-8601 含时区，来源 user/import/system/model。model 无法成为默认可信事实。
6. 用可信用户确认供应 confirmed；不要让模型自行批准。不要自动导入整段聊天，不与宿主原生 Memory 自动同步。
7. Adapter 负责串行化写操作、候选文件隐私和清理、明确的项目边界，以及展示冲突供用户决定。调用 get/export 可查看历史，不能把历史状态重新当成有效规则。

Hermes reference adapter 展示 subprocess CLI 方式。其他 Agent 可实现相同命令协议，无需依赖 Hermes 或模型 SDK。
