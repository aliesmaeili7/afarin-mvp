"""grant the backend role explicit RLS access

Revision ID: 9f2b7c4d5e10
Revises: 0b876a2c1921
Create Date: 2026-08-11 15:12:04.881204

The previous migration enabled RLS with no policies at all, on the assumption
that afarin_app would hold BYPASSRLS. Hosted Supabase does not grant BYPASSRLS
to customer roles, and a role that is neither the table owner nor BYPASSRLS
matches no policy: reads return zero rows *silently* and writes raise
"new row violates row-level security policy". The API would have been locked
out of its own tables in production.

So the backend now gets its access from a policy naming it explicitly, and
stops depending on the role attribute. anon and authenticated still match no
policy and still hold no grants, so the browser-facing Data API sees nothing —
which was the only thing the deny-all was ever protecting.

This is not the authorization boundary. FastAPI checks ownership on every
request (spec §27); the policy is deliberately unconditional because the
backend legitimately reads across all users.
"""

from collections.abc import Sequence

from alembic import op

from app.db.models import APP_TABLES, BROWSER_ROLES, RUNTIME_ROLE

revision: str = "9f2b7c4d5e10"
down_revision: str | None = "0b876a2c1921"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICY = "afarin_app_full_access"


def upgrade() -> None:
    browser_roles = ", ".join(BROWSER_ROLES)
    for table in APP_TABLES:
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"drop policy if exists {POLICY} on {table}")
        op.execute(
            f"create policy {POLICY} on {table} "
            f"for all to {RUNTIME_ROLE} using (true) with check (true)"
        )
        # Re-asserted rather than assumed: a table added by a future migration
        # inherits default privileges, and this keeps the invariant in one place.
        op.execute(f"revoke all on table {table} from {browser_roles}")


def downgrade() -> None:
    for table in APP_TABLES:
        op.execute(f"drop policy if exists {POLICY} on {table}")
