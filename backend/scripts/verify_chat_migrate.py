"""
Apply the full Alembic chain to an empty database.

    uv run python -m scripts.verify_chat_migrate

Catches migration-order issues that an already-upgraded development database
hides. Uses a throwaway database on the local Supabase Postgres, then drops it.
Does not touch the running `postgres` database.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402

DB_NAME = os.environ.get("VERIFY_MIGRATE_DB", "afarin_chat_migrate_smoke")
EXPECTED_HEAD = "c5f8a2d01b34"
CHAT_TABLES = ("chat_conversations", "chat_messages", "chat_artifacts")

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "ok  " if condition else "FAIL"
    print(f"  [{mark}] {label}{f' — {detail}' if detail else ''}")
    if not condition:
        failures.append(label)


def admin_dsn(settings, database: str = "postgres") -> str:
    url = settings.admin_database_url.replace("postgresql+psycopg://", "postgresql://")
    return url.rsplit("/", 1)[0] + f"/{database}"


def migrator_url(settings, database: str) -> str:
    url = settings.migration_database_url
    return url.rsplit("/", 1)[0] + f"/{database}"


def terminate_and_drop(settings) -> None:
    with psycopg.connect(admin_dsn(settings), autocommit=True) as connection:
        connection.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity "
            "where datname = %s and pid <> pg_backend_pid()",
            (DB_NAME,),
        )
        connection.execute(f"drop database if exists {DB_NAME}")


def main() -> int:
    settings = get_settings()
    backend_root = Path(__file__).resolve().parents[1]

    print(f"\nFresh-database migration ({DB_NAME})")
    terminate_and_drop(settings)

    with psycopg.connect(admin_dsn(settings), autocommit=True) as connection:
        connection.execute(f"create database {DB_NAME}")
        connection.execute(f"grant connect on database {DB_NAME} to afarin_migrator")
        connection.execute(f"grant connect on database {DB_NAME} to afarin_app")
        connection.execute(f"grant create on database {DB_NAME} to afarin_migrator")

    with psycopg.connect(admin_dsn(settings, DB_NAME), autocommit=True) as connection:
        connection.execute("create extension if not exists pgcrypto")
        connection.execute("grant usage, create on schema public to afarin_migrator")
        connection.execute("grant usage on schema public to afarin_app")
        connection.execute(
            "alter default privileges for role afarin_migrator in schema public "
            "grant select, insert, update, delete on tables to afarin_app"
        )
        connection.execute(
            "alter default privileges for role afarin_migrator in schema public "
            "grant usage, select on sequences to afarin_app"
        )

    env = os.environ.copy()
    env["MIGRATION_DATABASE_URL"] = migrator_url(settings, DB_NAME)
    # New process: get_settings() must not reuse the parent cache.
    env.pop("PYTHONPATH", None)

    print("  running alembic upgrade head…")
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=backend_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        check("alembic upgrade head", False, f"exit {result.returncode}")
        terminate_and_drop(settings)
        return 1
    check("alembic upgrade head", True)

    with psycopg.connect(admin_dsn(settings, DB_NAME)) as connection:
        head = connection.execute("select version_num from alembic_version").fetchone()
        check(
            "head revision is chat Phase B",
            bool(head) and head[0] == EXPECTED_HEAD,
            head[0] if head else "missing",
        )
        existing = {
            row[0]
            for row in connection.execute(
                "select tablename from pg_tables where schemaname = 'public'"
            )
        }
        for table in CHAT_TABLES:
            check(f"created {table}", table in existing)
        fk = connection.execute(
            """
            select exists (
              select 1
              from information_schema.table_constraints
              where table_name = 'chat_conversations'
                and constraint_type = 'FOREIGN KEY'
                and constraint_name like '%user_id%'
            )
            """
        ).fetchone()
        check("chat_conversations.user_id references profiles", bool(fk and fk[0]))
        swatch = connection.execute(
            """
            select column_name from information_schema.columns
            where table_name = 'chat_conversations' and column_name = 'active_theme_json'
            """
        ).fetchone()
        check("semantic theme column exists", swatch is not None)

    terminate_and_drop(settings)
    check("throwaway database dropped", True)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
