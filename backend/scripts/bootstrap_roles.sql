-- One-time role bootstrap.
--
-- Run with the Supabase `postgres` admin connection BEFORE the first Alembic
-- migration: Alembic authenticates as afarin_migrator and therefore cannot be
-- the thing that creates it.
--
-- Idempotent: safe to re-run on an existing database.
--
-- ${MIGRATOR_PASSWORD} and ${APP_PASSWORD} are substituted as quoted literals
-- by scripts/bootstrap.py.

-- afarin_migrator owns the schema and runs migrations. DDL only.
--
-- As the table owner it is exempt from RLS unless FORCE ROW LEVEL SECURITY is
-- set. That is left alone on purpose: it is used by Alembic and by nothing that
-- serves a request, and forcing RLS would break future data migrations.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'afarin_migrator') then
    execute format('create role afarin_migrator login password %L', ${MIGRATOR_PASSWORD});
  else
    execute format('alter role afarin_migrator login password %L', ${MIGRATOR_PASSWORD});
  end if;
end
$$;

-- afarin_app is the API's runtime connection: DML only, no DDL.
--
-- Deliberately NOT BYPASSRLS, and deliberately not a member of the owner role.
-- Hosted Supabase refuses to grant BYPASSRLS to customer roles, so anything
-- that depended on it would work locally and fail in production. Instead every
-- table carries an RLS policy naming afarin_app (migration 9f2b7c4d5e10).
--
-- RLS is not the authorization boundary either way: FastAPI checks ownership on
-- every request (spec §27). RLS exists to keep the browser-facing Data API out.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'afarin_app') then
    execute format('create role afarin_app login password %L', ${APP_PASSWORD});
  else
    execute format('alter role afarin_app login password %L', ${APP_PASSWORD});
  end if;
end
$$;

-- Undo both shortcuts an earlier version of this script took, so a database
-- bootstrapped before the fix converges on the same least-privilege shape as a
-- hosted one. Either statement may be refused on a managed project; that is
-- fine, because there it was never granted in the first place.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'afarin_app' and rolbypassrls) then
    alter role afarin_app nobypassrls;
    raise notice 'removed BYPASSRLS from afarin_app; it now relies on its RLS policy';
  end if;
exception when insufficient_privilege then
  raise notice 'cannot alter BYPASSRLS on afarin_app; assuming it does not have it';
end
$$;

do $$
begin
  if pg_has_role('afarin_app', 'afarin_migrator', 'member') then
    revoke afarin_migrator from afarin_app;
    raise notice 'revoked owner-role membership from afarin_app';
  end if;
exception when insufficient_privilege then
  raise notice 'cannot revoke afarin_migrator from afarin_app';
end
$$;

-- Supabase's `postgres` role is privileged but not a superuser, and
-- ALTER DEFAULT PRIVILEGES FOR ROLE requires membership of that role.
do $$
begin
  execute format('grant afarin_migrator to %I', current_user);
end
$$;

grant usage, create on schema public to afarin_migrator;
grant usage on schema public to afarin_app;

-- Deliberately no grants on the `auth` schema.
--
-- It is owned by supabase_admin, and even the `postgres` admin role holds USAGE
-- and REFERENCES on auth.users without grant option, so these privileges cannot
-- be passed to a custom role on either a local or a hosted project. Ownership
-- columns therefore reference profiles.user_id, which lives in a schema we own
-- (see app/db/base.py:user_fk).

-- The point of bootstrapping first: every table a later migration creates
-- grants DML to afarin_app automatically, so no migration has to remember.
alter default privileges for role afarin_migrator in schema public
  grant select, insert, update, delete on tables to afarin_app;
alter default privileges for role afarin_migrator in schema public
  grant usage, select on sequences to afarin_app;

-- Catch up anything created before this script ran.
grant select, insert, update, delete on all tables in schema public to afarin_app;
grant usage, select on all sequences in schema public to afarin_app;
