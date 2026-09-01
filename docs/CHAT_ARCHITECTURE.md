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
        chat persistence services
             ↓
        Postgres + private storage
```

React components talk only to `ChatApi`. They do not import campaign APIs, education APIs, Supabase, or model providers.

---

## Phases

### Phase A — Chat UX (done)

Persian-first RTL workspace at `/chat` and `/chat/[conversationId]`. Desktop sidebar, mobile drawer, composer, `+` menu, action chips, theme chip, attachments, account menu, history, rename/pin/archive/delete, text-only share, mock image artifacts.

### Phase B — Persistent conversations (this document)

User-owned conversations, messages, artifacts, theme snapshots, and history. No Orchestrator. No LLM. No image model. No advertising or education generation.

### Phase C — Orchestrator + skills (not implemented)

`sendMessage()` will persist the user turn, then run a Persian-native Orchestrator that routes to Advertising, Education, or general chat. The Chat API remains the user-facing seam. Do not call campaign/education routes from React.

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
- **http:** persists the user message only. No fabricated assistant. Phase C will add the assistant turn to the same `ChatTurnResult`.

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

## Verification (Phase B)

Requires `supabase start`, the API on `:8000`, and the frontend on `:3000` with `NEXT_PUBLIC_API_MODE=http`.

```bash
cd backend && uv run python -m scripts.verify_chat_migrate
cd backend && uv run python -m scripts.verify_chat_flow
cd frontend && npm run verify:chat:http
```

`verify:chat` (no `:http`) is the Phase A mock UI walk and does not prove persistence.
