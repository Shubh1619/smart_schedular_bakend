from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
else:
    connect_args = {
        "connect_timeout": 5,
        "keepalives": 1,           # Enable TCP keepalives
        "keepalives_idle": 30,     # Start keepalives after 30s idle
        "keepalives_interval": 10, # Retry every 10s
        "keepalives_count": 5,     # Drop after 5 failed probes
    }
    engine = create_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=300,  # Recycle connections every 5 min
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)