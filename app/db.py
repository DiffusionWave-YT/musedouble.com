import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.config import settings

log = logging.getLogger("musedouble.db")


class Base(DeclarativeBase):
    pass


engine = create_engine(settings().database_url.get_secret_value(), pool_size=5, max_overflow=5,
                       pool_pre_ping=True, pool_timeout=10, connect_args={"connect_timeout": 5})
SessionLocal = sessionmaker(engine, expire_on_commit=False)
# Authenticated requests and audit writes use separate pools so audit and rate writes
# cannot starve each other when the main pool is saturated.
security_engine = create_engine(settings().database_url.get_secret_value(), pool_size=2, max_overflow=0,
                                pool_pre_ping=True, pool_timeout=3, connect_args={"connect_timeout": 5})
SecuritySessionLocal = sessionmaker(security_engine, expire_on_commit=False)


# Side effects (handing a job to Redis, publishing progress) must only happen once the
# database change they describe is committed. Callers register them on the session;
# they run after a real commit and are discarded on rollback.
@event.listens_for(Session, "after_commit")
def _run_after_commit(session):
    for hook in session.info.pop("after_commit", []):
        try:
            hook()
        except Exception:
            log.warning("after_commit_hook_failed hook=%s", getattr(hook, "__name__", "?"))


@event.listens_for(Session, "after_rollback")
def _discard_after_commit(session):
    session.info.pop("after_commit", None)


def after_commit(session, hook):
    session.info.setdefault("after_commit", []).append(hook)


def database():
    with SessionLocal.begin() as db:
        yield db
