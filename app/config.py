from functools import lru_cache
from pathlib import Path
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MUSE_", env_file=ROOT / ".env", extra="ignore")
    env: str = "local"
    database_url: SecretStr
    encryption_key: SecretStr
    signing_key: SecretStr
    web_origin: str = "http://127.0.0.1:3001"
    api_origin: str = "http://127.0.0.1:8010"
    object_origin: str = "http://127.0.0.1:9011"
    allowed_gpu_hosts: str = "127.0.0.1,localhost"
    cookie_secure: bool = False
    storage: Path = ROOT / "storage"
    session_hours: int = 8
    max_active_jobs: int = 2
    worker_lease_seconds: int = 90
    job_timeout_seconds: int = 900
    queue_timeout_seconds: int = 300
    max_attempts: int = 3
    upload_limit: int = 20 * 1024 * 1024
    upload_daily_limit: int = 200 * 1024 * 1024
    output_limit: int = 32 * 1024 * 1024
    # Redis: cola ARQ, límites de tasa y progreso (pub/sub). Servicio compartido:
    # el prefijo aísla las claves de MuseDouble de otros proyectos.
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")
    redis_prefix: str = "musedouble:"
    worker_concurrency: int = 4
    # Un trabajo queued sin reenvío a la cola se vuelve a encolar tras este plazo.
    requeue_after_seconds: int = 60

    @field_validator("storage")
    @classmethod
    def resolve_storage(cls, value: Path) -> Path:
        path = value if value.is_absolute() else ROOT / value
        return path.resolve()

    @field_validator("signing_key")
    @classmethod
    def signing_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("Signing key must have at least 32 characters")
        return value


@lru_cache
def settings() -> Settings:
    return Settings()
