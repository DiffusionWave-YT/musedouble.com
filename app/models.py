import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(12), default="member")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    can_generate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("role IN ('admin','member')"),)


class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(100), default="")
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ModelProfile(Base):
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    character_prompt: Mapped[str] = mapped_column(Text, default="")
    eye_prompt: Mapped[str] = mapped_column(Text, default="")
    loras: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AppSetting(Base):
    __tablename__ = "app_settings"
    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB)


class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer, default=1)
    cost: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    graph: Mapped[dict] = mapped_column(JSONB)
    sha256: Mapped[str] = mapped_column(String(64))
    contract: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("cost > 0"), CheckConstraint("mode IN ('generate','reference')"))


class GpuServer(Base):
    __tablename__ = "gpu_servers"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    url_enc: Mapped[str] = mapped_column(Text)
    token_enc: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    healthy: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    busy_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    __table_args__ = (UniqueConstraint("busy_job_id"),)


class GpuWorkflow(Base):
    __tablename__ = "gpu_server_workflows"
    gpu_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gpu_servers.id", ondelete="CASCADE"), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True)


class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    object_key: Mapped[str] = mapped_column(String(200))
    mime: Mapped[str] = mapped_column(String(40))
    size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"))
    workflow_version: Mapped[int] = mapped_column(Integer)
    workflow_mode: Mapped[str] = mapped_column(String(16), default="generate")
    graph: Mapped[dict] = mapped_column(JSONB)
    model_name: Mapped[str] = mapped_column(String(120))
    model_snapshot: Mapped[dict] = mapped_column(JSONB)
    params: Mapped[dict] = mapped_column(JSONB)
    request_key: Mapped[str] = mapped_column(String(80))
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[int] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    gpu_server_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gpu_servers.id"))
    comfy_prompt_id: Mapped[str | None] = mapped_column(String(80))
    client_id: Mapped[str | None] = mapped_column(String(80))
    dispatch_state: Mapped[str] = mapped_column(String(16), default="not_sent")
    worker_id: Mapped[str | None] = mapped_column(String(80))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    error_public: Mapped[str | None] = mapped_column(String(200))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # Last time this job was handed to Redis; the sweeper requeues stale queued jobs.
    enqueued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("user_id", "request_key"),
        CheckConstraint("status IN ('queued','running','succeeded','failed','canceled')"),
        CheckConstraint("cost >= 0"),
        Index("jobs_queue", "created_at", postgresql_where=text("status = 'queued'")),
        Index("jobs_owner_created", "user_id", "created_at"),
    )


class CreditEntry(Base):
    __tablename__ = "credit_ledger"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(24))
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"))
    reference: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("job_id", "reason"),)


class Output(Base):
    __tablename__ = "job_outputs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), index=True)
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True)
    object_key: Mapped[str] = mapped_column(String(200))
    mime: Mapped[str] = mapped_column(String(40))
    size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
