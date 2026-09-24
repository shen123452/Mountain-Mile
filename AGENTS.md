# AGENTS.md — 给 AI 编程助手（Claude / Codex / 豆包）的项目指引

## 项目概要

山程 Mountain Mile 是一个 **agent 优先**的 3D 学习成长应用。

- 前端：Vue 3 + Vite + TypeScript + Tailwind CSS + Three.js（**不是 React / Next.js**）
- 后端：Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic + OpenAI Python SDK + APScheduler
- 数据库：PostgreSQL 16 + pgvector
- 云服务：阿里云百炼 DashScope（对话 + Embedding）· 阿里云 OSS（文件存储）

## 工作约定

- 完整设计与计划见 [`PRODUCT.md`](./PRODUCT.md) 与 [`docs/开发文档.md`](./docs/开发文档.md)，按其中里程碑推进，不擅自扩大范围。
- **一次只做一个里程碑**：当前任务以 [`TASKS.md`](./TASKS.md) 为准；完成并通过其完成标准（DoD）后提交、push，然后**停下等人工验收**，不自行进入下一个里程碑。
- 密钥只放在 `backend/.env`（已被 gitignore），禁止写进代码、日志或提交。
- 地形生成、SM-2 复习、agent 编排为框架无关的纯逻辑，优先实现并补充测试。
- 前端组件遵循项目视觉令牌（青绿山水世界），提交前可用 impeccable 检测器检查。

## 参考项目与移植边界

- 参考实现位于同级目录 **`../summer-checkin`（MIT）**：其 agent 运行时、工具定义、记忆 / RAG 逻辑、体素地形数学**允许对照移植**，但必须：
  1. 后端 TS → **Python（FastAPI + openai SDK）**，不使用 Vercel AI SDK；
  2. 前端 React → **Vue 3**；
  3. 落地本项目的差异化能力：多角色协作、SSE 流式、自主档位、观测台、SM-2 复习；
  4. 移植代码落地时在 `NOTICE.md` 保留 MIT 归属与原作者声明；
  5. 不复制其品牌名与雨林 / 雪 / 暖云主题。
- 遇到文档未覆盖的歧义，选最简单的方案并在汇报中列出。

## 产品原则

你有权对我的看法提出质疑，觉得不好就按你的来；产品不是越复杂越好，用户喜欢简约、易上手的功能。
