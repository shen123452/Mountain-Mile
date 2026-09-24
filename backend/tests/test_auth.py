import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, RefreshToken


@pytest.mark.asyncio
async def test_auth_lifecycle() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def test_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            unauthorized = await client.get("/auth/me")
            assert unauthorized.status_code == 401
            assert unauthorized.json()["error"]["code"] == "HTTP_401"
            created = await client.post("/auth/register", json={
                "email": " Student@Example.com ", "name": "山程用户", "password": "secure-pass-123"
            })
            assert created.status_code == 201
            assert created.json()["data"]["email"] == "student@example.com"
            assert "HttpOnly" in created.headers["set-cookie"]
            old_refresh = client.cookies.get("mm_refresh")
            assert old_refresh
            async with sessions() as session:
                stored = await session.scalar(select(RefreshToken.token_hash))
                assert stored and stored != old_refresh
            assert (await client.get("/auth/me")).status_code == 200
            assert (await client.post("/auth/register", json={
                "email": "student@example.com", "name": "Duplicate", "password": "secure-pass-123"
            })).status_code == 409

            refreshed = await client.post("/auth/refresh")
            assert refreshed.status_code == 200
            assert client.cookies.get("mm_refresh") != old_refresh
            current_refresh = client.cookies.get("mm_refresh")
            client.cookies.clear()
            client.cookies.set("mm_refresh", current_refresh, domain="testserver.local", path="/")
            client.cookies.set("mm_access", "invalid-access-token", domain="testserver.local", path="/")
            assert (await client.get("/auth/me")).status_code == 401
            assert (await client.post("/auth/refresh")).status_code == 200
            assert (await client.get("/auth/me")).status_code == 200
            async with AsyncClient(transport=transport, base_url="http://testserver") as replay:
                replay.cookies.set("mm_refresh", old_refresh)
                assert (await replay.post("/auth/refresh")).status_code == 401

            before_logout = client.cookies.get("mm_refresh")
            assert (await client.post("/auth/logout")).status_code == 200
            assert (await client.get("/auth/me")).status_code == 401
            assert (await client.post("/auth/refresh")).status_code == 401
            async with AsyncClient(transport=transport, base_url="http://testserver") as replay:
                replay.cookies.set("mm_refresh", before_logout)
                assert (await replay.post("/auth/refresh")).status_code == 401
            assert (await client.post("/auth/login", json={
                "email": "student@example.com", "password": "wrong-pass"
            })).status_code == 401
            assert (await client.post("/auth/login", json={
                "email": "student@example.com", "password": "超" * 30
            })).status_code == 401
            assert (await client.post("/auth/login", json={
                "email": "student@example.com", "password": "secure-pass-123"
            })).status_code == 200
            assert (await client.get("/auth/me")).status_code == 200
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
