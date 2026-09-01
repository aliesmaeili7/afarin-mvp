# Chat architecture

Afarin chat is a **third product surface**, not a Campaign and not an EducationalPost.

```text
React Chat UI
     ↓
ChatApi
     ├── mockChatApi   (Phase A demo / tests)
     └── httpChatApi   (NEXT_PUBLIC_API_MODE=http)
             ↓
        /api/chat
             ↓
        chat persistence  →  Orchestrator (services/orchestrator)
                                    ↓
                          Advertising / Education / General image / Image edit skills
                                    ↓
                          existing Creative Agent / EducationalAgent / ImageProvider
```

React components talk only to `ChatApi`. They do not import campaign APIs, education APIs, Supabase, or model providers. Skills call Python services in-process. Persistence modules under `services/chat` do not import providers.

---

## Phases

### Phase A — Chat UX (done)

Persian-first RTL workspace at `/chat` and `/chat/[conversationId]`. Desktop sidebar, mobile drawer, composer, `+` menu, action chips, theme chip, attachments, account menu, history, rename/pin/archive/delete, text-only share, mock image artifacts.

### Phase B — Persistent conversations (done)

User-owned conversations, messages, artifacts, theme snapshots, and history.

### Phase C — Orchestrator + skills (done)

Paid routes persist `activity_phase` on the generating assistant (`preparing_*` → `generating_image` → ads-only `finalizing`). Phase writes merge one JSONB key and are best-effort. The frontend polls `getConversation` and shows `ChatActivityIndicator`; unhinted text uses a client-only thinking state. No extra model calls.

Explicit chips skip the Orchestrator LLM. Artifact language is still detected deterministically (e.g. «متن انگلیسی باشه») and is never copied from reply language.

Skills:

- **Education** — internal `EducationalPost`, existing educational generator. Chat artifact references the education storage path.
- **Advertising** — internal `Campaign` + product image from the chat attachment/reference, Creative Agent. Chat artifact references campaign candidate paths.
- **General image** — `ImageProvider` with `GENERAL_IMAGE_MODEL` (default `openai/gpt-image-2`). Bytes live under `chat/{id}/artifacts/`.

Deleting a conversation removes only `chat/` storage objects.

### Phase D — Conversational image editing (done)

Current-conversation reference resolution plus an internal `image_edit` skill. Edits are **reference-conditioned generation** via `ImageRequest.references` (`CHAT_IMAGE_EDIT_MODEL`, default `openai/gpt-image-2`), not mask/inpainting. Every edit creates a new chat-owned artifact under `chat/{id}/artifacts/` with lineage in `metadata_json`. Campaign and EducationalPost records are not mutated.

“Use as reference” sends `reference_artifact_ids`; the server re-checks ownership. Direct changes (“روشن‌ترش کن”) route to `image_edit`. “Another version” returns to the originating creation skill. For advertising regenerations, the original campaign product photo is reused; the rendered ad is not used as the product image unless the user explicitly asks.

Activity: `preparing_edit` → `generating_image` → `ready`. Chat artifacts may be `1:1`, `4:5`, or `9:16`.

Memory, voice, music, video, subtitles, projects, and cross-chat asset libraries remain future work.

---

## Auth

Reuses Afarin session (`useChatAccount` → `useSessionStore`). No second auth store.

- Only signed-in users persist history.
- Every conversation is owner-scoped.
- Anonymous visitors may use `/chat` as a local draft. Send in HTTP mode stashes the draft and goes to `/login?next=/chat`.
- Opening `/chat` never creates a database row.

---

## Database

Tables: `chat_conversations`, `chat_messages`, `chat_artifacts`.

Ownership: `user_id` NOT NULL → `profiles.user_id`. No anonymous DB owner.

`active_theme_json` is a **semantic snapshot** `{ id, source, name, style_json }`. The frontend derives swatches from the catalog. Do not persist CSS.

Action chips persist per message as `metadata_json.explicit_skill_hint`. A conversation is not permanently “an education chat”.

---

## Lazy creation

`POST /api/chat/conversations` creates the conversation **and** the first user message in one Postgres transaction.

Object-storage upload is **not** part of that transaction. Bytes are validated first; upload happens after flush (needs the conversation id for the key); on upload failure the DB transaction rolls back and any uploaded object is removed.

---

## HTTP vs mock

`NEXT_PUBLIC_API_MODE` selects the implementation (same switch as campaigns).

- **mock:** seeded threads, fake assistant replies, mock artifacts. Offline UI demo.
- **http:** persists the user message, then the Orchestrator (or explicit hint) produces the assistant turn in the same `ChatTurnResult`. Generating artifacts poll via `GET /conversations/{id}`.

---

## Pagination

- Conversation list: `limit` (default 50) + `offset`. Phase B UI loads one page.
- Messages: latest page, `limit` default 200, `before` cursor, `has_older_messages`. Phase B UI does not infinite-scroll.

Sidebar “Today / Yesterday” grouping uses the user’s local timezone from ISO timestamps. The backend does not group by UTC day.

---

## Storage

Keys: `chat/{conversation_id}/attachments/{token}.{ext}` and `.../artifacts/...` in the existing `product-images` bucket.

Signed URLs go through `POST /api/assets/resolve`. `owner_scope` kind `chat` uses `get_owned_chat_conversation`. Holding a path is not a capability. Unknown and foreign conversation ids both 404.

---

## Share

Text copy / `navigator.share()` only. `publicUrl` is always null. No public RLS.

---

## Verification

Requires `supabase start`, the API on `:8000`, and the frontend on `:3000` with `NEXT_PUBLIC_API_MODE=http`.

```bash
cd backend && uv run python -m scripts.verify_chat_migrate
cd backend && uv run python -m scripts.verify_chat_flow
cd frontend && npm run verify:chat:http
```

Live Orchestrator routing (no images):

```bash
cd backend && uv run python -m scripts.eval_chat_router
```

Phase C HTTP/live browser smoke (paid image turns; several minutes):

```bash
cd frontend && npm run verify:chat:phase-c
```

`verify:chat` (no `:http`) is the mock UI walk, including Phase D reference-chip edits. It does not prove persistence.
