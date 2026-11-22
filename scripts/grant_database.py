from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from app.config import ROOT

config = dotenv_values(ROOT / ".env")
engine = create_engine(config["MUSE_MIGRATION_DATABASE_URL"])
with engine.begin() as db:
    for statement in [
        "REVOKE ALL ON SCHEMA public FROM PUBLIC",
        "GRANT USAGE ON SCHEMA public TO musedouble_app",
        "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO musedouble_app",
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO musedouble_app",
        "REVOKE ALL ON TABLE alembic_version FROM musedouble_app",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO musedouble_app",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO musedouble_app",
    ]:
        db.execute(text(statement))
print("Permisos locales aplicados: API sin superusuario ni propiedad del esquema.")
