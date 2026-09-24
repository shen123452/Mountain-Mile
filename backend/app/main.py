from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.goals import router as goals_router
from app.api.agent import router as agent_router
from app.api.focus import router as focus_router
from app.api.conversations import router as conversations_router
from app.api.reports import router as reports_router
from app.api.schedules import router as schedules_router
from app.scheduler.jobs import build_scheduler

_scheduler = build_scheduler()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _scheduler.start()
    try:
        yield
    finally:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="Mountain Mile API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(goals_router)
app.include_router(agent_router)
app.include_router(focus_router)
app.include_router(conversations_router)
app.include_router(reports_router)
app.include_router(schedules_router)


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "请求参数不正确"}},
    )


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
