FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 依赖层:与 backend/pyproject.toml 保持一致,单独成层以复用构建缓存
# 目标服务器在国内,固定使用阿里云 PyPI 镜像,否则直连 PyPI 会超时
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --timeout 60 --retries 3 \
    "fastapi>=0.115" "uvicorn[standard]>=0.30" "sqlalchemy[asyncio]>=2.0.30" \
    "alembic>=1.13" "asyncpg>=0.29" "pgvector>=0.3" "openai>=1.40" \
    "pydantic>=2.8" "pydantic-settings>=2.4" "pyjwt>=2.9" "bcrypt>=4.2" \
    "python-multipart>=0.0.9" "apscheduler>=3.10" "pypdf>=5.0" \
    "python-docx>=1.1" "oss2>=2.18" "httpx>=0.27" "sse-starlette>=2.0"

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

EXPOSE 4000

# 单 worker:目标机器内存有限,启动时先跑迁移
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 4000 --workers 1"]
