# AI Coding 研发记忆库 (MCP)

![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![MCP Streamable HTTP](https://img.shields.io/badge/MCP-Streamable_HTTP-2563EB)
![SQLite FTS5 + sqlite-vec](https://img.shields.io/badge/SQLite-FTS5_%2B_sqlite--vec-003B57?logo=sqlite&logoColor=white)
![Embedding](https://img.shields.io/badge/BGE-bge--small--zh--v1.5-F59E0B)
![MkDocs Material](https://img.shields.io/badge/MkDocs-Material-526CFE?logo=materialformkdocs&logoColor=white)

面向 **Claude Code、Codex、Cursor** 等多工具协同研发场景的本地/团队级上下文与研发经验管理服务。基于 **Git** 维护项目确定性规范（`AGENTS.md` / `CLAUDE.md`），通过 **Basic Memory + MCP 协议** 沉淀历史排障经验与技术方案，结合 **SQLite FTS5 (BM25) + 本地中文 Embedding (`bge-small-zh-v1.5`)** 混合检索与 **MkDocs** 知识站，实现跨会话记忆读写与团队知识共享。

![一图看懂 AI Coding 研发记忆库](docs/assets/comic-overview.svg)

---

## 核心特性

- **规范与经验分层治理**：确定性架构约束随代码库 Git 维护（`AGENTS.md` / `CLAUDE.md`）；动态排障案例与技术决策通过 MCP 沉淀为标准 Markdown 笔记。
- **关键词 + 中文语义混合检索**：集成 `SQLite FTS5 (BM25)`（精准匹配错误码、异常类名、配置项）与 `sqlite-vec` + 本地 `BAAI/bge-small-zh-v1.5`（512 维中文语义向量召回），无需外部 API Key。
- **多工具统一 MCP 接入**：基于 `Streamable HTTP`（`:8000/mcp`）统一对接 Claude Code、Codex、Cursor，支持写入前查重（`search_notes`）、结构化落盘（`write_note`）与关联图谱上下文组装（`build_context`）。
- **AI 写笔记 = 自动发文档**：`Material for MkDocs`（`:8088`）只读监听同一笔记目录，AI 沉淀的 Markdown 实时渲染为可检索的 Web 知识站。

---

## 快速启动

### 方式一：Docker Compose（推荐）

支持 Linux `x86_64` / `ARM64` 及 Apple Silicon。首次启动自动缓存约 96 MB 的 `bge-small-zh-v1.5` 权重并初始化示例笔记。

```bash
docker compose up --build --wait --wait-timeout 420
docker compose ps
```

| 服务组件 | 默认地址 | 职责说明 |
| :--- | :--- | :--- |
| **Basic Memory MCP** | `http://localhost:8000/mcp` | 供 Claude Code / Codex / Cursor 检索、读取、写入笔记 |
| **MkDocs 知识站** | `http://localhost:8088/` | 人类浏览器实时查阅同一批 Markdown 笔记 |
| **BGE 中文向量服务** | 容器内 `http://embedding:8001/v1` | 本地 CPU 推理生成 512 维 L2 归一化中文向量 |

> 端口冲突时，将 [.env.example](.env.example) 复制为 `.env` 并修改 `MCP_PORT` 或 `SITE_PORT`。

### 方式二：本机直接运行（无 Docker，基于 `uv`）

```bash
uv sync --locked --managed-python --python 3.12
uv run --locked python -m coding_memory local
```

本机模式按 `Embedding (:8001) → MCP (:8000) → MkDocs (:8088)` 顺序拉起子进程，数据默认存放在 `var/`（笔记 `var/notes`、SQLite 索引 `var/config`、模型缓存 `var/cache`），按 `Ctrl+C` 一键优雅退出。

---

## 接入你的开发项目

直接复制 [examples/client-project](examples/client-project) 下的配置文件到你的业务代码仓库：

| 客户端 / 规范文件 | 配置文件路径 | 作用 |
| :--- | :--- | :--- |
| **Claude Code** | [`.mcp.json`](examples/client-project/.mcp.json) + [`CLAUDE.md`](examples/client-project/CLAUDE.md) | 声明 `:8000/mcp` 端点与查重沉淀规则 |
| **Codex CLI** | [`.codex/config.toml`](examples/client-project/.codex/config.toml) + [`AGENTS.md`](examples/client-project/AGENTS.md) | 配置 MCP Server 与仓库级检索过滤规则 |
| **Cursor** | [`.cursor/mcp.json`](examples/client-project/.cursor/mcp.json) | 接入统一 Streamable HTTP MCP 服务 |

**日常研发对话示例：**
- **检索历史经验**：「先查一下记忆库，`pay-ledger` 以前遇到 `ERR_ACCOUNT_LOCK_TIMEOUT` 热点账户行锁超时是怎么解决的？」
- **查重并沉淀经验**：「把这次定位的根因、修复方案和验证结果沉淀到记忆库，写入前先查重。」

---

## 端到端冒烟验证

内置零依赖端到端验证模块，自动校验 **MCP 握手 $\rightarrow$ 全文/向量/混合三路检索 $\rightarrow$ 临时笔记写入读回 $\rightarrow$ MkDocs 页面实时发布与清理**：

```bash
# 校验 MCP 工具发现与 text / vector / hybrid 三种检索召回
python3 -m coding_memory.verify

# 额外执行 write_note -> read_note -> MkDocs 页面渲染 -> delete_note 完整闭环校验
python3 -m coding_memory.verify --write-check
```

---

## 目录结构

```text
.
├── compose.yaml                 # Docker Compose 三服务编排 (embedding / memory / site)
├── Dockerfile                   # 多阶段 uv 构建镜像
├── mkdocs.yml                   # Material for MkDocs 中文知识站配置
├── pyproject.toml               # Python 3.12 依赖分组定义 (memory / embedding / site)
├── coding_memory/
│   ├── config.py                # 核心运行时配置与目录映射 (RuntimeConfig)
│   ├── encoder.py               # FastAPI OpenAI 兼容向量服务 (BAAI/bge-small-zh-v1.5)
│   ├── __main__.py              # 服务统一入口与本机多进程编排器 (memory / embedding / site / local)
│   └── verify.py                # MCP Streamable HTTP + 混合检索 + 知识站端到端验证套件
├── examples/
│   ├── client-project/          # 业务仓库接入模板 (AGENTS.md / CLAUDE.md / .mcp.json / .codex / .cursor)
│   └── notes/                   # 示例研发记忆笔记 (troubleshooting / architecture / solution)
└── docs/
    ├── assets/comic-overview.svg # 四格漫画与全链路架构图
    └── architecture.md          # 检索与写入底层调用机制说明
```

## 许可证

[MIT License](LICENSE)
