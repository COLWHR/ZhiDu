from __future__ import annotations

import logging
import os
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.session import db_manager
from utils import LLMServiceError

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


try:
    db_manager.init_db()
except Exception as exc:
    logger.error("Database initialization failed: %s", exc, exc_info=True)


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback

    error_id = uuid.uuid4().hex[:12]
    logger.error("Global exception [%s]: %s\n%s", error_id, exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "detail": "Internal server error",
            "message": "服务器内部错误，请稍后重试",
            "error_id": error_id,
            "data": None,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "detail": exc.detail,
            "message": exc.detail,
            "data": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error: %s", exc.errors())
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "detail": exc.errors(),
            "message": "请求参数验证失败",
            "data": None,
        },
    )


@app.exception_handler(LLMServiceError)
async def llm_service_exception_handler(request: Request, exc: LLMServiceError):
    logger.error("LLM service error on %s (%s): %s", request.url.path, exc.kind, exc.details or exc.message)

    if request.url.path.startswith(f"{settings.API_V1_STR}/agents/chat"):
        return JSONResponse(
            status_code=200,
            content={
                "content": f"抱歉，时空之门当前无法调用大模型服务：{exc.message}",
                "thought": None,
            },
        )

    return JSONResponse(
        status_code=503,
        content={
            "code": 503,
            "detail": exc.message,
            "message": exc.message,
            "data": None,
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "Cache-Control"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

base_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(base_dir)

uploads_dir = os.path.join(root_dir, "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

frontend_dist = os.path.join(root_dir, "frontend", "dist")
if not os.path.exists(frontend_dist):
    frontend_dist = os.path.join(root_dir, "..", "frontend", "dist")

logger.info("Frontend dist path: %s, exists: %s", frontend_dist, os.path.exists(frontend_dist))

if os.path.exists(frontend_dist):
    legacy_assets_dir = os.path.join(frontend_dist, "assets")
    modern_assets_dir = os.path.join(frontend_dist, "static")

    if os.path.exists(legacy_assets_dir):
        app.mount("/assets", StaticFiles(directory=legacy_assets_dir), name="assets")

    if os.path.exists(modern_assets_dir):
        app.mount("/static", StaticFiles(directory=modern_assets_dir), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            return JSONResponse(status_code=404, content={"detail": "API endpoint not found"})

        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

        return JSONResponse(status_code=404, content={"detail": "Not Found"})


@app.get("/")
def root():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to MADF API. Frontend not found.", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
