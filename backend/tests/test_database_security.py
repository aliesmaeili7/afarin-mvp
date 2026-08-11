"""
Guards the database's security posture, not the API's.

Every other test in this suite reaches Postgres as afarin_app, which is
NOBYPASSRLS and not the table owner — the same shape a hosted Supabase project
forces on us. So the suite as a whole already proves the backend can work under
RLS. What is asserted here is that it stays that way: an accidental BYPASSRLS
grant, a missing policy on a new table, or a stray grant to `anon` would all
pass every other test while quietly changing what a leaked key can reach.
"""

import uuid

import pytest
from sqlalchemy import text

from app.db.models import APP_TABLES, BROWSER_ROLES, OWNER_ROLE, RUNTIME_ROLE
from app.db.session import get_sessionmaker


async def fetch_all(sql: str, **params: object) -> list[tuple]:
    async with get_sessionmaker()() as session:
        result = await session.execute(text(sql), params)
        return [tuple(row) for row in result.all()]


async def fetch_one(sql: str, **params: object):
    rows = await fetch_all(sql, **params)
    return rows[0][0]


async def test_the_runtime_role_does_not_hold_bypassrls() -> None:
    """
    The bug this file exists for.

    BYPASSRLS cannot be granted on hosted Supabase. If it is ever switched on
    locally the tests below stop meaning anything, because RLS would no longer
    be exercised at all.
    """
    bypasses = await fetch_one(
        "select rolbypassrls from pg_roles where rolname = :role", role=RUNTIME_ROLE
    )
    assert bypasses is False


async def test_the_runtime_role_is_not_the_table_owner() -> None:
    """Owner membership also bypasses RLS, and carries DDL with it."""
    is_member = await fetch_one(
        "select pg_has_role(:app, :owner, 'member')",
        app=RUNTIME_ROLE,
        owner=OWNER_ROLE,
    )
    assert is_member is False


async def test_the_runtime_role_cannot_change_the_schema() -> None:
    async with get_sessionmaker()() as session:
        with pytest.raises(Exception) as caught:
            await session.execute(text("create table rls_probe (id int)"))
    assert "permission denied" in str(caught.value).lower()


async def test_every_table_enforces_row_level_security() -> None:
    rows = await fetch_all(
        "select tablename from pg_tables "
        "where schemaname = 'public' and rowsecurity is false"
    )
    unprotected = {row[0] for row in rows} & set(APP_TABLES)
    assert unprotected == set()


async def test_only_the_backend_role_has_a_policy() -> None:
    """
    A policy for any other role would be a second, unreviewed way in.

    `roles` is the list a policy applies to; anything other than exactly
    afarin_app means someone widened access.
    """
    rows = await fetch_all(
        "select tablename, policyname, roles::text[], cmd, permissive "
        "from pg_policies where schemaname = 'public'"
    )
    covered = {}
    for tablename, policyname, roles, cmd, permissive in rows:
        assert list(roles) == [RUNTIME_ROLE], f"{tablename}.{policyname} -> {roles}"
        assert cmd == "ALL", f"{tablename}.{policyname} is only {cmd}"
        assert permissive == "PERMISSIVE"
        covered.setdefault(tablename, []).append(policyname)

    assert set(covered) == set(APP_TABLES), "a table is missing its backend policy"
    for tablename, policies in covered.items():
        assert len(policies) == 1, f"{tablename} has {len(policies)} policies"


@pytest.mark.parametrize("role", BROWSER_ROLES)
@pytest.mark.parametrize("privilege", ["select", "insert", "update", "delete"])
async def test_browser_roles_hold_no_table_privileges(
    role: str, privilege: str
) -> None:
    """
    The publishable key is in every visitor's browser. These two roles are what
    it authenticates as, so they must reach nothing in our schema.
    """
    granted = await fetch_all(
        "select tablename from pg_tables where schemaname = 'public' "
        "and has_table_privilege(:role, schemaname || '.' || tablename, :privilege)",
        role=role,
        privilege=privilege,
    )
    assert {row[0] for row in granted} & set(APP_TABLES) == set()


async def test_the_backend_can_still_read_and_write_through_its_policy() -> None:
    """
    The other half of the bug: with RLS on and no policy, this insert failed and
    the follow-up select silently returned nothing.
    """
    user_id = uuid.uuid4()
    async with get_sessionmaker()() as session:
        await session.execute(
            text(
                "insert into profiles (user_id, display_name) "
                "values (:user_id, 'rls check')"
            ),
            {"user_id": user_id},
        )
        await session.commit()

        visible = await session.execute(
            text("select display_name from profiles where user_id = :user_id"),
            {"user_id": user_id},
        )
        assert visible.scalar_one() == "rls check"

        await session.execute(
            text("update profiles set display_name = 'renamed' where user_id = :u"),
            {"u": user_id},
        )
        await session.execute(
            text("delete from profiles where user_id = :user_id"), {"user_id": user_id}
        )
        await session.commit()
