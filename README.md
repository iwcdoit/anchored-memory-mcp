# AI Coding 研发记忆库 (MCP)

![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![MCP Streamable HTTP](https://img.shields.io/badge/MCP-Streamable_HTTP-2563EB)
![SQLite FTS5 + sqlite-vec](https://img.shields.io/badge/SQLite-FTS5_%2B_sqlite--vec-003B57?logo=sqlite&logoColor=white)
![Embedding](https://img.shields.io/badge/BGE-bge--small--zh--v1.5-F59E0B)
![MkDocs Material](https://img.shields.io/badge/MkDocs-Material-526CFE?logo=materialformkdocs&logoColor=white)

面向 **Claude Code、Codex、Cursor** 等多工具协同研发场景的本地/团队级上下文与研发经验管理服务。基于 **Git** 维护项目确定性规范（AGENTS.md / CLAUDE.md / .ai 目录），通过 **Basic Memory + MCP 协议** 沉淀历史排障经验与技术方案，结合 **SQLite FTS5 (BM25) + 本地中文 Embedding (bge-small-zh-v1.5)** 混合检索与 **MkDocs** 知识站，实现跨会话记忆读写与团队知识共享。

![一图看懂 AI Coding 研发记忆库](docs/assets/comic-overview.svg)

---

## 核心机制：按需加载与按需读写执行流

在多微服务研发场景下，多个独立的业务 Git 仓库共享同一个 Basic Memory MCP 服务。为了避免一上来将所有文档和历史记忆塞进上下文导致 Token 爆炸，AI 客户端遵循严格的**四步按需触发链路**：

### 第一步：项目级配置挂载 MCP 服务
每个业务子仓库根目录下放置客户端配置文件（Claude Code 读取 .mcp.json，Codex 读取 .codex/config.toml，Cursor 读取 .cursor/mcp.json），将工具统一接入共享的 Streamable HTTP MCP 服务端（:8000/mcp）。

### 第二步：自动读取子项目 AGENTS.md 入口与底部钩子
AI 进入具体微服务项目时，首先读取该项目根目录下的 **AGENTS.md**（**CLAUDE.md** 仅包含一行 @AGENTS.md 引用同一事实源，消除多工具规则漂移），获取当前项目的模块划分、Maven/脚本构建测试命令与代码红线；同时通过文件末尾的钩子指令，接管后续的按需加载策略：

```markdown
# Agent Instructions (位于各子项目 AGENTS.md 底部)
Read and follow .ai/AI_CONTEXT.md and .ai/MEMORY_POLICY.md before starting work.
Apply any more-specific AGENTS.md files within their directory scope.
```

### 第三步：本地静态规范按需路由（由 .ai/AI_CONTEXT.md 控制）
明确禁止 AI 递归预加载整个 docs 目录，仅根据当前任务类型按需读取对应文档：
- **日常编码与测试**：按需读取 docs/development/conventions.md 开发规约。
- **跨模块与架构变更**：按需读取 docs/architecture/ 模块边界说明与 docs/adr/ 架构决策记录。
- **长周期任务续接**：按需读取 docs/tasks/ 下的任务追踪文档。

### 第四步：远端 Basic Memory 按需检索与沉淀（由 .ai/MEMORY_POLICY.md 与 Skills 控制）
多个微服务项目物理共用同一个记忆库，逻辑上通过 **repository** 元数据实现项目级隔离与按需读写：
- **Git 上下文自动溯源**：读写记忆前，AI 先执行 .ai/scripts/get-developer-context.sh，自动从 Git 提取当前项目的确定性 repository 名称、branch、commit 与 developer_id。
- **按需检索（memory-continue）**：仅在排查历史疑难故障、改动高风险模块或跨会话续接工作时触发。优先限定当前项目作用域调用混合检索（BM25 精确匹配错误码/类名 + BGE 中文向量语义召回），必要时沿 Relations 关系图谱做二跳扩展：
  ```python
  # 1. 限定当前微服务仓库作用域，按需混合检索
  search_notes(
      project="main",
      query="ERR_ACCOUNT_LOCK_TIMEOUT 热点账户行锁超时",
      metadata_filters={"repository": "pay-ledger"},
  )
  # 2. 命中核心笔记后，按需拉取全文或沿 [[Relations]] 图谱构建关联上下文
  build_context(url="memory://projects/pay-ledger/troubleshooting/hot-account-lock-timeout", depth=2)
  ```
- **按需写入与查重合成（memory-capture / memory-notes）**：仅在确认故障根因、修复方案验证通过或形成关键技术决策时触发。写入前必须先调用 search_notes 查重——已有同类笔记则原地合成覆写（Synthesize, don't append，拒绝碎片化流水账）；无则按 6 大标准分类（incident 线上故障 / debugging 排查过程 / solution 解决方案 / pitfall 技术陷阱 / practice 工程实践 / task-context 长任务上下文）写入：
  ```python
  write_note(
      project="main",
      title="热点账户行锁超时排查",
      directory="projects/pay-ledger/troubleshooting",
      content="# 热点账户行锁超时排查\n\n...(根因、修复与验证)...\n\n## Observations\n- [root_cause] ...\n- [fix] ...\n\n## Relations\n- relates_to [[交易终态事件驱动编排规范]]",
      metadata={
          "repository": "pay-ledger",
          "memory_type": "troubleshooting",
          "status": "verified",
          "branch": "master",
      },
  )
  ```
- **三态知识晋升闭环（status）**：
  **draft**（排查中的假设与初步证据） $\rightarrow$ **verified**（经测试或线上验证的确切方案） $\rightarrow$ **promoted**（当经验沉淀为长期强制规范时，反哺写入 Git 仓库的 docs/adr/ 或 conventions.md，并将记忆标记为已晋升）。

---

## 快速启动服务端

### 方式一：Docker Compose（推荐）

支持 Linux x86_64 / ARM64 及 Apple Silicon。首次启动自动缓存约 96 MB 的 bge-small-zh-v1.5 权重并初始化示例笔记。

```bash
docker compose up --build --wait --wait-timeout 420
docker compose ps
```

| 服务组件 | 默认地址 | 职责说明 |
| :--- | :--- | :--- |
| **Basic Memory MCP** | http://localhost:8000/mcp | 供 Claude Code / Codex / Cursor 按需检索、读取、写入笔记 |
| **MkDocs 知识站** | http://localhost:8088/ | 人类浏览器实时查阅同一批 Markdown 笔记 |
| **BGE 中文向量服务** | 容器内 http://embedding:8001/v1 | 本地 CPU 推理生成 512 维 L2 归一化中文向量 |

> 端口冲突时，将 .env.example 复制为 .env 并修改 MCP_PORT 或 SITE_PORT。

### 方式二：本机直接运行（无 Docker，基于 uv）

```bash
uv sync --locked --managed-python --python 3.12
uv run --locked python -m coding_memory local
```

### 端到端冒烟验证

```bash
# 校验 MCP 握手与 text(错误码) / vector(中文语义) / hybrid 三路检索
python3 -m coding_memory.verify

# 额外校验 write_note -> read_note -> MkDocs 实时渲染 -> delete_note 闭环
python3 -m coding_memory.verify --write-check
```

---

## 业务仓库一键接入模板与核心配置

将 examples/client-project/ 下的文件复制到任意业务微服务仓库根目录即可完成接入：

```text
your-service-repo/
├── AGENTS.md                           # 子项目模块结构、构建测试命令与底部 .ai 钩子入口
├── CLAUDE.md                           # 单行 @AGENTS.md 引用，保持多工具规范单一事实源
├── .mcp.json                           # Claude Code MCP 接入配置
├── .codex/config.toml                  # Codex CLI MCP 接入配置
├── .cursor/mcp.json                    # Cursor MCP 接入配置
├── .ai/
│   ├── AI_CONTEXT.md                   # 本地 docs/ (conventions / adr / tasks) 按需路由规则
│   ├── MEMORY_POLICY.md                # 远端 MCP 检索、查重、6 大分类、脱敏与三态晋升策略
│   └── scripts/get-developer-context.sh# 自动提取 Git repository / branch / commit / developer 元数据
└── .agents/skills/
    ├── memory-continue/SKILL.md        # 跨会话按需检索与关系图谱遍历指引
    ├── memory-capture/SKILL.md         # 会话结论查重与原地合成覆写指引
    └── memory-notes/SKILL.md           # Frontmatter + Observations + Relations 结构化笔记规范
```

**各客户端 MCP 接入配置明细：**

- **Claude Code（.mcp.json）与 Cursor（.cursor/mcp.json）**：
  ```json
  {
    "mcpServers": {
      "basic-memory": {
        "type": "http",
        "url": "http://localhost:8000/mcp"
      }
    }
  }
  ```
- **Codex CLI（.codex/config.toml）**：
  ```toml
  [mcp_servers.basic-memory]
  url = "http://localhost:8000/mcp"
  ```

---

## 服务端仓库结构

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
│   ├── client-project/          # 业务仓库分层接入脚手架 (AGENTS.md + .ai/ + 3 Skills)
│   └── notes/                   # 示例研发记忆笔记 (troubleshooting / architecture / solution)
└── docs/
    └── assets/comic-overview.svg# 四格漫画与全链路架构图
```

## 许可证

MIT License
