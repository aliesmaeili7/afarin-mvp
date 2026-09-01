# Afarin backend

FastAPI service that owns persistence, authentication and object storage.
Implements the `AfarinApi` contract the frontend already had, so the browser
never talks to Postgres or Supabase Storage directly.

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

## Local setup

```bash
# 1. Start Postgres, Auth, Storage and a mail catcher (needs Docker).
cd .. && supabase start

# 2. Configure. The defaults already match the local Supabase stack.
cd backend && cp .env.example .env
#    Then set SUPABASE_SERVICE_ROLE_KEY from `supabase status`.

# 3. Create the database roles. Runs as the `postgres` admin.
uv run python -m scripts.bootstrap

# 4. Apply the schema. Runs as afarin_migrator.
uv run alembic upgrade head

# 5. Serve.
uv run uvicorn app.main:app --reload --port 8000
```

Then point the frontend at it with `NEXT_PUBLIC_API_MODE=http`.

Educational smoke harness (stub by default, no paid calls):

```bash
uv run python -m scripts.run_education_eval
uv run python -m scripts.run_education_eval --case fa_math_decimals --no-image
```

Two end-to-end checks, both against the running stack:

```bash
uv run python -m scripts.verify_flow   # the API contract, incl. the emailed code
cd ../frontend && node scripts/verify-ui.mjs   # the same journey in a browser
```

## Hosted Supabase

`supabase start` reads `supabase/config.toml`, so local development needs no
clicking. A hosted project does not read that file — these five things must be
set by hand in the dashboard, and nothing else:

1. **Authentication → Sign In / Providers → Email.** Enable email sign-up.
   Under **Email Templates → Magic Link**, paste
   `supabase/templates/magic_link.html`. This is the important one: the default
   template sends a link, and the app asks for a six-digit code. The template
   must contain `{{ .Token }}`, not `{{ .ConfirmationURL }}`. Leave
   **Reset Password** as a link (`{{ .ConfirmationURL }}`) pointing at
   `/auth/reset-password` so OTP-only accounts can set a password.
2. **Authentication → Sign In / Providers → Google.** Enable it and paste the
   client ID and secret from Google Cloud. Add
   `https://<project-ref>.supabase.co/auth/v1/callback` as an authorised
   redirect URI on the Google side.
3. **Authentication → URL Configuration.** Set the site URL to the deployed
   frontend and add `<frontend-origin>/auth/callback` and
   `<frontend-origin>/auth/reset-password` to the redirect
   allow-list. Google sign-in fails silently without it.
4. **Database → Connection string.** Use the `postgres` URI as
   `ADMIN_DATABASE_URL` for the one-time bootstrap, then run
   `alembic upgrade head`. Nothing here needs `BYPASSRLS`, which Supabase does
   not grant — see below.
5. **Project Settings → API.** Copy the service-role key into
   `SUPABASE_SERVICE_ROLE_KEY` in the backend environment only. It must never
   reach `frontend/.env.local`. On the same page, set **Exposed schemas** to
   drop `public`, matching `[api] schemas` in `supabase/config.toml`.

Storage buckets are *not* manual: the API creates `product-images` and
`brand-assets` as private buckets on startup if they are missing.

In production also set `ANON_COOKIE_SECURE=true`, and `ANON_COOKIE_SAMESITE=none`
if the API is on a different site than the frontend.

## Database roles

Three connections, deliberately separated:

| Role | Used by | Rights |
| --- | --- | --- |
| `postgres` | `scripts/bootstrap.py`, once | Admin. Creates the other two. |
| `afarin_migrator` | Alembic | Owns the tables. DDL. |
| `afarin_app` | The running API | `SELECT/INSERT/UPDATE/DELETE` only. No DDL, no `TRUNCATE`. |

Bootstrap must run first: Alembic authenticates as `afarin_migrator`, so it
cannot be the thing that creates it.

## Keeping the browser out of the database

FastAPI is the authorization boundary. It checks ownership on every request
(spec §27), and nothing below replaces that. These three layers exist so that a
leaked publishable key, or a mistake in one layer, still reaches nothing.

1. **The Data API does not expose `public`.** The browser uses supabase-js for
   auth only; every table read goes through FastAPI. PostgREST therefore has no
   reason to see our schema, and doesn't.
2. **`anon` and `authenticated` hold no grants** on any application table.
3. **RLS is enabled on every table**, with a single policy per table naming
   `afarin_app`. Any other role matches no policy and reads nothing.

`afarin_app` is deliberately **not** `BYPASSRLS` and **not** a member of the
owner role. Hosted Supabase refuses to grant `BYPASSRLS` to customer roles, and
a role that is neither owner nor `BYPASSRLS` matches no policy at all: reads
return zero rows *silently* and writes fail. An earlier version of this project
assumed otherwise and would have been locked out of its own tables in
production. Relying on the policy instead means local and hosted behave
identically, and the whole test suite — which connects as `afarin_app` —
exercises the production configuration on every run.

`tests/test_database_security.py` asserts all of the above, including that
`afarin_app` never regains `BYPASSRLS`.

## Layout

```
app/
  api/v1/        HTTP surface, one module per resource
  core/          config, errors, JWT verification, request principal, cookies
  db/            SQLAlchemy models and the session factory
  content/       Persian copy fixtures (ported from the Phase 1 mock)
  providers/     ContentProvider protocol; stub or OpenRouter via CONTENT_PROVIDER
  services/      campaign, identity and storage logic
migrations/      Alembic
scripts/         bootstrap, end-to-end verification
```

## LLM provider (Phase 3)

`CONTENT_PROVIDER=stub` uses the deterministic Persian fixtures. Tests always
run this way and never call a paid API.

`CONTENT_PROVIDER=openrouter` sends concept and copy requests to OpenRouter.
Set `OPENROUTER_API_KEY` in this backend environment only — never in the
frontend. Switch models with `LLM_MODEL` (default `openai/gpt-5-mini`); no UI
control exists for this.

If the key is missing while the provider is `openrouter`, the API returns a
Persian generation error. It does not silently fall back to fixtures.

Optional live check (makes a real paid call):

```bash
OPENROUTER_API_KEY=... uv run pytest -m live
```

Compare models later with `uv run python -m scripts.eval_llm`.

Image generation uses the same OpenRouter image provider for both paths, with
separate models:

* `IMAGE_MODEL` (default `bytedance-seed/seedream-4.5`) — advertising only
* `EDUCATIONAL_IMAGE_MODEL` (default `openai/gpt-image-2`) — educational posts only

`IMAGE_PROVIDER=stub` never calls OpenRouter. Tests always run that way.

Creative image/Director lab (dev only, never part of the wizard):

```bash
uv run python -m scripts.run_creative_eval --case sweatshirt_01 --mode fixed --dry-run
```

See `eval/README.md`.


## Notes for later phases

- `generation_jobs` records provider, model, tokens, latency and cost for LLM
  calls. Phase 4 will add image-generation jobs on the same table.
- `campaign_assets.storage_path` is null throughout Phase 3. The browser
  composes each ad from `metadata_json`; once a renderer writes real files, the
  path takes over with no frontend change.
- Phone/SMS sign-in is deliberately out of scope. It slots in beside email in
  `app/api/v1/session.py` without touching the ownership model.
