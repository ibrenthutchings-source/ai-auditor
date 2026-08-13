import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# pool_pre_ping so a stale/dropped connection (e.g. DB restarted) is
# detected and reconnected rather than surfacing as a write failure.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Session:
    return SessionLocal()


def init_db() -> None:
    """Create tables if they don't exist. Never raises -- a missing/
    unreachable database must not prevent the API from starting; audit
    persistence degrades to a no-op (see persist_audit_record) rather than
    taking the whole service down. Called once at FastAPI startup.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        logger.warning("init_db: could not reach database, persistence disabled for this run", exc_info=True)
