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

🚧 开发中（M0 脚手架已完成，等待人工验收）

## 本地启动（M0）

需要 Python 3.13、uv、Node 20+、pnpm 和 Docker。先运行 `docker compose up -d db`；容器的 PostgreSQL 映射到本机 `5434`，避免与已有的 `5432` 服务冲突。

在 `backend/` 运行 `uv sync`、`uv run alembic upgrade head`、`uv run uvicorn app.main:app --port 4000`。在 `frontend/` 运行 `pnpm install`、`pnpm dev`。打开 `http://localhost:5173`；`/api/health` 会代理到后端，后端文档位于 `http://localhost:4000/docs`。

## 许可

待补充。Agent 与体素地形的部分实现移植自 MIT 项目，将在 `NOTICE.md` 中保留归属声明。
