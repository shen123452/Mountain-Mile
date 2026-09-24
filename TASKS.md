# TASKS.md — 开发任务清单

## 给 Codex 的工作纪律

1. **一次只做一个里程碑**：当前任务见下方「当前任务」，严格按步骤与完成标准（DoD）执行。
2. 完成并通过 DoD 后：`git add → commit → push`，然后**停下汇报**，等人工确认再进入下一个里程碑。
3. 不擅自扩大范围；文档未覆盖的歧义，选最简单的方案并在汇报中列出。
4. 后端 Python（FastAPI + openai SDK），前端 Vue 3；参考项目 `../summer-checkin`（MIT）仅用于对照移植，移植规则见 `AGENTS.md`。
5. `backend/.env` 含真实密钥，禁止提交。

## 总进度

- [ ] **M0 脚手架** ← 当前任务
- [ ] M1 认证（bcrypt + JWT + refresh）
- [ ] M2 体素地形引擎移植
- [ ] M3 目标 CRUD + 群岛总览
- [ ] M4 Agent 运行时 + 14 工具 + 审批持久化
- [ ] M5 专注 / 打卡联动 + 岛屿生长
- [ ] M6 对话 + 报告 + APScheduler 调度
- [ ] M7 SSE 流式时间线 + 中断 / 断点续跑
- [ ] M8 多角色 + 自主档位 / 权限
- [ ] M9 记忆 + RAG（pgvector、上传、curate）
- [ ] M10 观测台 + SM-2 复习 + 分析工具
- [ ] M11 统计 / 资料 / 记忆管理
- [ ] M12 落地页 + 响应式 + impeccable audit / polish
- [ ] M13 部署（Docker / Nginx / HTTPS / README / 演示视频）

---

# 当前任务：M0 脚手架

## 目标

搭好可运行的 monorepo：**FastAPI 后端 + Vite/Vue 前端 + PostgreSQL(pgvector)**，全部能一键启动；目录结构与开发文档第 15 节一致。

## 步骤

### A. 包管理准备

1. 启用 pnpm（Node 22 自带 corepack）：`corepack enable pnpm`
2. 安装 uv（若未装）：`pip install uv`

### B. 后端 `backend/`

1. 在 `backend/` 用 uv 初始化（**保留已存在的 `.env` / `.env.example` / `.gitignore`，不要覆盖**）：`uv init --python 3.12`
2. 按开发文档 3.3 添加依赖：`fastapi`、`uvicorn[standard]`、`sqlalchemy[asyncio]`、`alembic`、`asyncpg`、`pgvector`、`openai`、`pydantic`、`pydantic-settings`、`pyjwt`、`bcrypt`、`python-multipart`、`apscheduler`、`pypdf`、`python-docx`、`oss2`、`httpx`
3. 创建应用骨架：
   - `app/main.py`：FastAPI 实例；`GET /health` 返回 `{ "status": "ok" }`；按 `CORS_ORIGINS` 配置 CORS（允许凭证）。
   - `app/core/config.py`：用 pydantic-settings 的 BaseSettings 读取 `.env` 中全部变量。
   - `app/core/database.py`：async engine（DATABASE_URL）+ `AsyncSessionLocal` + `get_db` 依赖。
4. 初始化 Alembic（异步模板）：`uv run alembic init -t async alembic`；配置 `sqlalchemy.url = DATABASE_URL`、`target_metadata = Base.metadata`；在首个迁移中执行 `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`。
5. 能启动：`uv run uvicorn app.main:app --reload --port 4000`，可访问 `/health` 与 `/docs`。

### C. 前端 `frontend/`

1. 在仓库根执行：`pnpm create vite frontend --template vue-ts`
2. 安装依赖：`tailwindcss`（按 Vite 插件方式初始化到 `src/styles/`）、`three`、`vue-router`、`pinia`、`@vueuse/core`
3. 清理模板示例内容；配置 vue-router 占位路由（`/`、`/login`、`/agent`、`/world`）与 pinia。
4. `vite.config.ts` 中把 `/api` 代理到 `http://localhost:4000`；`pnpm dev` 在 5173 启动。

### D. 根 `docker-compose.yml`

1. service `db`：镜像 `pgvector/pgvector:pg16`；环境变量 `POSTGRES_DB=mountain_mile`、`POSTGRES_USER=postgres`、`POSTGRES_PASSWORD=postgres`；端口 `5432:5432`；挂载数据卷。
2. backend / frontend 的容器化可留到 M13，本里程碑不要求。

### E. `NOTICE.md`

- 创建 `NOTICE.md`：声明本项目的 agent 运行时、工具体系、记忆 / RAG 逻辑与体素地形数学移植自参考项目 **summer-checkin（MIT）**，保留原作者版权声明；具体移植文件在后续里程碑补充。

## 完成标准（DoD，逐项自检）

- [ ] `docker compose up -d db` 后 PostgreSQL 可连接，`vector` 扩展已创建。
- [ ] 后端 `uv run uvicorn app.main:app --port 4000` 启动，`GET /health` 返回 ok，`/docs` 可访问。
- [ ] 前端 `pnpm dev` 启动，首页可打开，`/api` 请求能代理到后端。
- [ ] `uv run alembic upgrade head` 执行成功。
- [ ] `git status` 中**不出现 `backend/.env`**。
- [ ] 目录结构与开发文档第 15 节一致（`backend/app/...`、`frontend/src/...` 骨架就位）。
- [ ] 已提交并 push，commit message：`feat(M0): 搭建前后端 monorepo 脚手架`。

## 人工验收命令

```powershell
docker compose up -d db
docker compose exec db psql -U postgres -d mountain_mile -c "SELECT extname FROM pg_extension;"
# backend
cd backend; uv run uvicorn app.main:app --port 4000   # 访问 http://localhost:4000/health 与 /docs
# frontend
cd frontend; pnpm dev                                # 访问 http://localhost:5173
```

---

## M1 及以后

待 M0 人工验收通过后再展开；各里程碑目标与验收门见 `docs/开发文档.md` 第 16 节。
