# 山程 Mountain Mile

> 学习如登山，每一步都算数。

一个 **agent 优先（agent-first）的 3D 学习成长应用**：多角色学习智能体（规划者 / 执行者 / 复盘者 / 记忆官 / 向导）通过工具调用真实地运转计划、专注、打卡、知识库与记忆；每个学习目标，都是一座随这些动作生长的青绿体素山屿。

## 技术栈

- **前端**：Vue 3 · Vite · TypeScript · Tailwind CSS · Three.js
- **后端**：Python · FastAPI · SQLAlchemy 2.0 · Alembic · OpenAI SDK · APScheduler
- **数据库**：PostgreSQL 16 + pgvector
- **云服务**：阿里云百炼 DashScope（对话 + Embedding）· 阿里云 OSS（文件存储）

## 文档

- 产品定义：[`PRODUCT.md`](./PRODUCT.md)
- 开发文档：[`docs/开发文档.md`](./docs/开发文档.md)

## 状态

🚧 开发中（M4 Agent 运行时与审批已完成）

## 本地启动（M0）

需要 Python 3.13、uv、Node 20+、pnpm 和 Docker。先运行 `docker compose up -d db`；容器的 PostgreSQL 映射到本机 `5434`，避免与已有的 `5432` 服务冲突。

在 `backend/` 运行 `uv sync`、`uv run alembic upgrade head`、`uv run uvicorn app.main:app --port 4000`。在 `frontend/` 运行 `pnpm install`、`pnpm dev`。打开 `http://localhost:5173`；`/api/health` 会代理到后端，后端文档位于 `http://localhost:4000/docs`。

M1 认证页面位于 `/register` 和 `/login`。后端提供 `/auth/register`、`/auth/login`、`/auth/me`、`/auth/refresh`、`/auth/logout`；前端通过 `/api/auth/*` 访问。访问令牌和可轮换的刷新令牌写入 httpOnly Cookie，刷新令牌的哈希存入 PostgreSQL。运行 `uv run pytest -q -p no:cacheprovider` 可验证认证流程。

M2 地形演示位于登录后的 `/terrain-demo`。可调整目标种子、四组青绿山水调色与解锁地块数，拖动旋转山屿。运行 `pnpm test` 验证地形快照，`pnpm build` 验证前端构建。M3 的 `/world` 使用 PostgreSQL 中的真实目标：新建后即生成固定山形，支持编辑、切换和归档。地块数目前固定为 20，学习记录驱动的生长将在 M5 接入。

M4 的 `/agent` 提供运行记录与审批工作台。创建运行时先读取计划、待办和今日任务，随后由 DashScope 模型选择工具。写操作默认暂停，用户可以批准、改参数或拒绝；运行记录和审批状态保存在 PostgreSQL。14 个工具已注册，其中计划、任务、待办的 10 个工具可执行；打卡、记忆、统计和知识库的 4 个工具会明确返回暂不可用，待后续里程碑接入。需要在 `backend/.env` 配置 `DASHSCOPE_API_KEY` 才能启动真实 Agent 运行。

M5 在 `/world` 提供专注开始/完成控制。专注记录和每日打卡使用 PostgreSQL 持久化；同一用户每天只能打卡一次。目标山屿地块数会根据完成专注分钟和关联打卡数实时增长，公式为 `20 + floor(专注分钟 / 8) + 打卡数 × 3`，最多显示全部地形块。

M6 增加 `/agent` 内的持久化学习对话，以及 `/reports/daily`、`/reports/weekly` 报告接口。`/agent/schedule` 支持标准五段 cron 配置，后端启动时由 APScheduler 每分钟检查到期任务；周日 20:00 生成周报通知。未配置 `DASHSCOPE_API_KEY` 时，对话仍会保存，定时运行会生成明确的失败通知。

## 许可

待补充。Agent 与体素地形的部分实现移植自 MIT 项目，将在 `NOTICE.md` 中保留归属声明。
