# AGENTS.md — 给 AI 编程助手（Claude / Codex / 豆包）的项目指引

## 项目概要

山程 Mountain Mile 是一个 **agent 优先**的 3D 学习成长应用。

- 前端：Vue 3 + Vite + TypeScript + Tailwind CSS + Three.js（**不是 React / Next.js**）
- 后端：Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic + OpenAI Python SDK + APScheduler
- 数据库：PostgreSQL 16 + pgvector
- 云服务：阿里云百炼 DashScope（对话 + Embedding）· 阿里云 OSS（文件存储）

## 工作约定

- 完整设计与计划见 [`PRODUCT.md`](./PRODUCT.md) 与 [`docs/开发文档.md`](./docs/开发文档.md)，按其中里程碑推进，不擅自扩大范围。
- 密钥只放在 `backend/.env`（已被 gitignore），禁止写进代码、日志或提交。
- 地形生成、SM-2 复习、agent 编排为框架无关的纯逻辑，优先实现并补充测试。
- 前端组件遵循项目视觉令牌（青绿山水世界），提交前可用 impeccable 检测器检查。

## 产品原则

你有权对我的看法提出质疑，觉得不好就按你的来；产品不是越复杂越好，用户喜欢简约、易上手的功能。
