import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.database import Base, engine
from app.routers import assignments, attachments, auth, schedule, teams

app = FastAPI(title=settings.app_name)

allowed_origins = []
for origin in [*settings.cors_origins, settings.frontend_base_url]:
    normalized = str(origin).strip().rstrip("/")
    if normalized and normalized not in allowed_origins:
        allowed_origins.append(normalized)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(schedule.router)
app.include_router(assignments.router)
app.include_router(attachments.router)


@app.on_event("startup")
def initialize_database_schema():
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)


@app.exception_handler(OperationalError)
async def db_operational_error_handler(_, exc: OperationalError):
    logging.exception("Database connectivity error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Database is temporarily unreachable. "
                "Please check DB/network connectivity and retry."
            )
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
