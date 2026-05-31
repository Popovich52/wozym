from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import Base, engine
from app.routes.agent import router as agent_router
from app.routes.auth import router as auth_router
from app.routes.messengers import router as messengers_router
from app.routes.me import router as me_router
from app.routes.platform import router as platform_router
from app.routes.teams import router as teams_router


def ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "marketplace_products" not in table_names:
        return
    columns = {column["name"] for column in inspector.get_columns("marketplace_products")}
    statements: list[str] = []
    dialect = engine.dialect.name.lower()

    if "image_urls_json" not in columns:
        if dialect == "postgresql":
            statements.append("ALTER TABLE marketplace_products ADD COLUMN image_urls_json JSON NOT NULL DEFAULT '[]'::json")
        else:
            statements.append("ALTER TABLE marketplace_products ADD COLUMN image_urls_json JSON NOT NULL DEFAULT '[]'")
    if "video_urls_json" not in columns:
        if dialect == "postgresql":
            statements.append("ALTER TABLE marketplace_products ADD COLUMN video_urls_json JSON NOT NULL DEFAULT '[]'::json")
        else:
            statements.append("ALTER TABLE marketplace_products ADD COLUMN video_urls_json JSON NOT NULL DEFAULT '[]'")

    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    yield


app = FastAPI(title="WOzYm - AI платформа продаж Backend", version="0.1.0", lifespan=lifespan)
app_log_level = logging.DEBUG if settings.app_env.lower() == "development" else logging.INFO
logging.basicConfig(level=app_log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
ai_asset_dir = Path(__file__).resolve().parent.parent / "runtime" / "ai-assets"
ai_asset_dir.mkdir(parents=True, exist_ok=True)

allowed_origins = {
    settings.web_url.rstrip("/"),
    "http://127.0.0.1:4412",
    "http://localhost:4412",
}
local_origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_origin_regex=local_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ai-assets", StaticFiles(directory=str(ai_asset_dir)), name="ai-assets")

app.include_router(auth_router)
app.include_router(me_router)
app.include_router(teams_router)
app.include_router(messengers_router)
app.include_router(agent_router)
app.include_router(platform_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "wozym-backend"}


@app.get("/debug/ports")
def debug_ports() -> dict[str, int]:
    return {
        "backend": 8617,
        "frontend": 4412,
        "postgres": 56432,
        "smtp": 11125,
        "mailpit": 18125,
    }


@app.get("/debug/cors")
def debug_cors() -> dict[str, object]:
    return {
        "allow_origins": sorted(allowed_origins),
        "allow_origin_regex": local_origin_regex,
        "allow_credentials": True,
    }

