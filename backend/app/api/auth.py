from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    ACCESS_COOKIE, REFRESH_COOKIE, create_access_token, create_refresh_token,
    hash_password, hash_refresh_token, utc_now, verify_password,
)
from app.models import RefreshToken, User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if value.count("@") != 1 or "." not in value.split("@", 1)[1] or any(ch.isspace() for ch in value):
            raise ValueError("邮箱格式不正确")
        return value

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("姓名不能为空")
        return value

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码过长")
        return value


class LoginBody(BaseModel):
    email: str
    password: str


class AutonomyBody(BaseModel):
    autonomy: str = Field(pattern=r"^L[012]$")


def public_user(user: User) -> dict[str, str]:
    return {"id": user.id, "email": user.email, "name": user.name, "autonomy": user.autonomy}


def set_auth_cookies(response: Response, user_id: str, refresh_token: str) -> None:
    common = {"httponly": True, "secure": settings.app_env == "production", "samesite": "lax", "path": "/"}
    response.set_cookie(ACCESS_COOKIE, create_access_token(user_id), max_age=settings.access_token_expire_minutes * 60, **common)
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=settings.refresh_token_expire_days * 86400, **common)


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")


def add_refresh_token(db: AsyncSession, user_id: str) -> str:
    token = create_refresh_token()
    db.add(RefreshToken(
        user_id=user_id, token_hash=hash_refresh_token(token),
        expires_at=utc_now() + timedelta(days=settings.refresh_token_expire_days),
    ))
    return token


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterBody, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password))
    db.add(user)
    try:
        await db.flush()
        refresh_token = add_refresh_token(db, user.id)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="该邮箱已注册") from exc
    set_auth_cookies(response, user.id, refresh_token)
    return {"data": public_user(user)}


@router.post("/login")
async def login(body: LoginBody, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    email = body.email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    refresh_token = add_refresh_token(db, user.id)
    await db.commit()
    set_auth_cookies(response, user.id, refresh_token)
    return {"data": public_user(user)}


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    old_token = request.cookies.get(REFRESH_COOKIE)
    if not old_token:
        raise HTTPException(status_code=401, detail="登录已过期")
    now = utc_now()
    user_id = await db.scalar(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(old_token), RefreshToken.revoked_at.is_(None), RefreshToken.expires_at > now)
        .values(revoked_at=now)
        .returning(RefreshToken.user_id)
    )
    if user_id is None:
        await db.rollback()
        raise HTTPException(status_code=401, detail="登录已过期")
    user = await db.get(User, user_id)
    if user is None:
        await db.rollback()
        raise HTTPException(status_code=401, detail="登录已过期")
    new_token = add_refresh_token(db, user_id)
    await db.commit()
    set_auth_cookies(response, user_id, new_token)
    return {"data": public_user(user)}


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(token), RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        await db.commit()
    clear_auth_cookies(response)
    return {"data": {"ok": True}}


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {"data": public_user(user)}


@router.patch("/autonomy")
async def update_autonomy(body: AutonomyBody, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    user.autonomy = body.autonomy
    await db.commit()
    await db.refresh(user)
    return {"data": public_user(user)}
