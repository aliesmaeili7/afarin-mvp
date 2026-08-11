"""
One-time database role bootstrap.

    uv run python -m scripts.bootstrap

Connects as the Supabase `postgres` admin role and creates afarin_migrator and
afarin_app. Must run before `alembic upgrade head`, because Alembic connects as
afarin_migrator and cannot create the role it is authenticating with.
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402

SQL_PATH = Path(__file__).with_name("bootstrap_roles.sql")


def _psycopg_dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+asyncpg://", "postgresql://"
    )


def render_sql(
    context: psycopg.Connection, migrator_password: str, app_password: str
) -> str:
    script = SQL_PATH.read_text(encoding="utf-8")
    return script.replace(
        "${MIGRATOR_PASSWORD}", sql.Literal(migrator_password).as_string(context)
    ).replace("${APP_PASSWORD}", sql.Literal(app_password).as_string(context))


def main() -> int:
    settings = get_settings()

    dsn = _psycopg_dsn(settings.admin_database_url)
    with psycopg.connect(dsn, autocommit=True) as connection:
        # Surfaces the BYPASSRLS fallback notice if the admin role cannot grant it.
        connection.add_notice_handler(lambda notice: print(notice.message_primary))
        statement = render_sql(
            connection,
            settings.afarin_migrator_password,
            settings.afarin_app_password,
        )
        with connection.cursor() as cursor:
            cursor.execute(statement)

    print("roles ready: afarin_migrator (DDL), afarin_app (DML, runtime)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
