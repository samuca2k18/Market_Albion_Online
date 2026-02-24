from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Garante que o pacote `app` seja encontrado ──────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Importa settings e os modelos para autogenerate ─────────────────────────
from app.core.config import settings   # noqa: E402
from app.database import Base          # noqa: E402
import app.models                      # noqa: E402, F401  ← registra todos os modelos

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Aponta para o metadata dos modelos (necessário para autogenerate) ────────
target_metadata = Base.metadata

# ── Injeta a URL do banco a partir do .env (ignora o placeholder do alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """Modo offline: gera SQL sem conectar ao banco."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online: conecta ao banco e aplica as migrações."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
