from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # Fail fast when remote DB is unreachable instead of hanging for a long time.
    connect_args = {"connect_timeout": 5}

engine = create_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
