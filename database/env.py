import os
from alembic import context
from sqlalchemy import create_engine, pool
from dotenv import load_dotenv
from app.config import ROOT, settings
from app.db import Base
import app.models  # noqa: F401  (side effect: registers models for autogenerate)

load_dotenv(ROOT / ".env")
url = os.environ.get("MUSE_MIGRATION_DATABASE_URL", settings().database_url.get_secret_value())
target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
