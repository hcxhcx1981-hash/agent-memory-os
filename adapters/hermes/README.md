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
