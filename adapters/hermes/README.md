# Hermes reference adapter

本目录是可复用适配器与 Skill 示例，未安装到当前 Hermes。不会修改现有 Memory、Skills、config，也不自动读历史。

## 安装

在独立项目内直接运行，无需复制 Core 到 Hermes。先阅读 SKILL.md；若想安装 Skill，由使用者手动复制本目录 SKILL.md 到自己 Hermes 的自定义 Skill 目录，并将其中 PROJECT_ROOT / STORE_PATH 替换为项目绝对路径及独立存储路径。不同 Hermes 版本的 Skill 目录不同，请按实际版本的自定义 Skill 安装方式操作。V0.1 未验证真实 Hermes 宿主安装，不宣称正式环境已集成。

## 调用

```python
from adapters.hermes.adapter import HermesAdapter
adapter = HermesAdapter('D:/fictional/agent-memory-os', 'D:/fictional/agent-memory-os/storage/hermes.json')
result = adapter.remember('examples/preference.json')
context = adapter.context('深色UI', 'Project-X')
```

remember 只通过 CLI evaluate → add，其他 decision 返回调用方处理。context 只通过 inject 取得最小上下文。候选文件需由调用方在明确确认后生成，不保存凭据、原始对话或猜测。

## 卸载与隔离

若手动安装过 Skill，只移除你自己复制的 Skill 文件及调用配置；保留本项目和数据，直到明确决定清理。不要改动 Hermes 原生 Memory。使用独立 storage/hermes.json；不双写、不合并原生记忆。程序自身从不编辑 Hermes 文件。


## Win10 thin Skill Router (V0.1.1)

已核准宿主 v0.21.5 的用户 Skills 机制。将 `ROUTER_SKILL.md` 手动复制到 Hermes home 的 `skills/agent-memory-os-router/SKILL.md`，不覆盖已有文件。使用 `chat-memory.bat` 从正常 CLI 进入，它仅为该会话预载 Skill 并限定 terminal,skills 工具，不改 Hermes config 或原生 Memory。普通无预载聊天只能靠宿主按描述发现 Skill，不保证自动加载；推荐专用入口。

Router 使用公共 CLI evaluate/add/retrieve/inject/supersede，独立数据为项目内 `storage/hermes-memory.json`。明确用户事实才确认写入，冲突须下一轮明确确认替换。模型推测不能作为用户确认。路由是 Skill 指令，不是强制 Hook；只承诺验收覆盖的用法。

最小事件证据在 `storage/hermes-router-events.jsonl`，仅时间、动作、ID、decision，不保存聊天或注入正文。运行数据已被 Git 忽略。卸载时用户可移除自己安装的独立 Skill；不用删除或迁移原生 Memory。

## V0.2 smart route

Existing write/read/supersede remain supported. write invokes Semantic Judge and the promotion/Core Gate path; read uses context-aware retrieval/injection. New observe --text stages a selected single preference; only after user confirmation may promote --id OBSERVATION_ID --user-confirmed write ACTIVE. --text supports raw factual assertions, --task and --machine provide retrieval scope. No per-message blanket queries or storage. Installed dedicated Skill is updated from ROUTER_SKILL.md; native Memory and other Skills remain untouched. Offline subprocess regression covers the entire original write/read/conflict/supersede chain; live host regression and IDs are in docs/hermes-v02-regression.md.
