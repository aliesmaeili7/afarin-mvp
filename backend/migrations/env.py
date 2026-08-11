from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.models import Base  # noqa: F401  (registers every model)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Alembic connects as afarin_migrator, which owns the schema. The role itself is
# created beforehand by scripts/bootstrap.py using the postgres admin
# connection, because a migration cannot create the role it authenticates with.
config.set_main_option(
    "sqlalchemy.url", get_settings().migration_database_url.replace("%", "%%")
)


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Supabase owns the auth/storage schemas; we only manage `public`."""
    return not (
        type_ == "table" and getattr(obj, "schema", None) not in (None, "public")
    )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
