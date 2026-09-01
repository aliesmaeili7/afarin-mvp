"""
Phase B chat persistence against a running stack.

    uv run python -m scripts.verify_chat_flow

Uses the real FastAPI backend, real Supabase Auth, real private storage.
No mocks, no LLM, no image model. Requires `supabase start` and the API on :8000.
"""

from __future__ import annotations

import io
import os
import re
import sys
import time
import uuid
from pathlib import Path

import httpx
import psycopg
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402

API = os.environ.get("VERIFY_API_URL", "http://127.0.0.1:8000")
MAIL = os.environ.get("VERIFY_MAIL_URL", "http://127.0.0.1:54324")

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "ok  " if condition else "FAIL"
    print(f"  [{mark}] {label}{f' — {detail}' if detail else ''}")
    if not condition:
        failures.append(label)


def tiny_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (48, 48), (196, 118, 52)).save(buffer, format="PNG")
    return buffer.getvalue()


def read_latest_code(client: httpx.Client, email: str) -> str | None:
    for _ in range(20):
        listing = client.get(f"{MAIL}/api/v1/messages").json()
        for message in listing.get("messages", []):
            recipients = [to.get("Address", "") for to in message.get("To", [])]
            if email not in recipients:
                continue
            body = client.get(f"{MAIL}/api/v1/message/{message['ID']}").json()
            found = re.search(r"\b(\d{6})\b", body.get("HTML") or body.get("Text", ""))
            if found:
                return found.group(1)
        time.sleep(0.5)
    return None


def signup(plain: httpx.Client, auth: str, anon_key: str, email: str) -> str:
    sent = plain.post(
        f"{auth}/otp",
        headers={"apikey": anon_key, "content-type": "application/json"},
        json={"email": email, "create_user": True},
    )
    check(f"code requested for {email}", sent.status_code in (200, 204), f"HTTP {sent.status_code}")
    code = read_latest_code(plain, email)
    check(f"code arrived for {email}", code is not None, code or "not received")
    if code is None:
        raise RuntimeError(f"no email code for {email}")
    verified = plain.post(
        f"{auth}/verify",
        headers={"apikey": anon_key, "content-type": "application/json"},
        json={"email": email, "token": code, "type": "email"},
    ).json()
    token = verified.get("access_token")
    check(f"access token for {email}", bool(token))
    if not token:
        raise RuntimeError(f"no access token for {email}")
    return token


def conversation_count(settings, user_id: str) -> int:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    with psycopg.connect(dsn) as connection:
        row = connection.execute(
            "select count(*) from chat_conversations where user_id = %s",
            (user_id,),
        ).fetchone()
        return int(row[0] if row else 0)


def main() -> int:
    settings = get_settings()
    anon_key = (
        os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or settings.supabase_service_role_key
    )
    auth = f"{settings.supabase_url.rstrip('/')}/auth/v1"
    stamp = int(time.time())
    email_a = f"chat-a-{stamp}@example.com"
    email_b = f"chat-b-{stamp}@example.com"

    api = httpx.Client(base_url=API, timeout=30.0)
    plain = httpx.Client(timeout=30.0)

    print("\n1. sign in account A")
    try:
        token_a = signup(plain, auth, anon_key, email_a)
    except RuntimeError:
        return report()
    headers_a = {"Authorization": f"Bearer {token_a}"}
    adopted = api.post("/api/session/adopt", headers=headers_a)
    check("profile created", adopted.status_code == 200, f"HTTP {adopted.status_code}")
    user_a = adopted.json()["user"]["id"]

    print("\n2. opening /chat must not create a row")
    before = conversation_count(settings, user_a)
    listed = api.get("/api/chat/conversations", headers=headers_a)
    check("list is empty", listed.status_code == 200 and listed.json() == [])
    check("no conversation row after list", conversation_count(settings, user_a) == before)

    anonymous = api.get("/api/chat/conversations")
    check("anonymous list is empty", anonymous.status_code == 200 and anonymous.json() == [])

    print("\n3. first Persian send creates one conversation")
    created = api.post(
        "/api/chat/conversations",
        json={"content": "سلام، این یک پیام فارسی است.", "language": "fa"},
        headers=headers_a,
    )
    check("first send succeeded", created.status_code == 200, created.text[:120])
    if created.status_code != 200:
        return report()
    conv_a = created.json()
    conv_a_id = conv_a["id"]
    check("one conversation row", conversation_count(settings, user_a) == before + 1)
    check("title is Persian", conv_a["title"].startswith("سلام"))
    check("only the user message", [m["role"] for m in conv_a["messages"]] == ["user"])
    check("no assistant invented", conv_a["artifacts"] == [])

    print("\n4. refresh keeps the message")
    again = api.get(f"/api/chat/conversations/{conv_a_id}", headers=headers_a).json()
    check(
        "message remains after reload",
        again["messages"][0]["content"] == "سلام، این یک پیام فارسی است.",
    )

    print("\n5. theme snapshot persists without CSS")
    themed = api.patch(
        f"/api/chat/conversations/{conv_a_id}",
        json={
            "active_theme": {
                "id": "saved-clay",
                "source": "chat_catalog",
                "name": "خمیری و بازیگوش",
                "style_json": {},
            }
        },
        headers=headers_a,
    )
    check("theme saved", themed.status_code == 200)
    reloaded = api.get(f"/api/chat/conversations/{conv_a_id}", headers=headers_a).json()
    check("theme remains after reload", reloaded["active_theme"]["id"] == "saved-clay")
    check("swatch not persisted", "swatch" not in (reloaded["active_theme"] or {}))

    print("\n6. image attachment survives reload")
    attached = api.post(
        f"/api/chat/conversations/{conv_a_id}/messages",
        files={
            "payload": (
                None,
                '{"content":"این عکس","language":"fa"}',
                "application/json",
            ),
            "attachment": ("smoke.png", tiny_png(), "image/png"),
        },
        headers=headers_a,
    )
    check("attachment upload succeeded", attached.status_code == 200, attached.text[:120])
    if attached.status_code != 200:
        return report()
    path = attached.json()["messages"][-1]["metadata_json"]["attachment"]["storage_path"]
    check("stored under chat/", "/chat/" in path and "/attachments/" in path)

    after_refresh = api.get(f"/api/chat/conversations/{conv_a_id}", headers=headers_a).json()
    stored = after_refresh["messages"][-1]["metadata_json"]["attachment"]["storage_path"]
    check("attachment path remains", stored == path)

    signed = api.post("/api/assets/resolve", json={"paths": [path]}, headers=headers_a).json()[path]
    check("owner can resolve attachment", bool(signed))
    if signed:
        fetched = plain.get(signed)
        check("signed URL serves the image", fetched.status_code == 200, f"{len(fetched.content)} bytes")

    print("\n7. second conversation appears in history")
    second = api.post(
        "/api/chat/conversations",
        json={"content": "گفتگوی دوم", "language": "fa"},
        headers=headers_a,
    )
    conv_b_id = second.json()["id"]
    history = api.get("/api/chat/conversations", headers=headers_a).json()
    ids = [item["id"] for item in history]
    check("both chats listed", set(ids) == {conv_a_id, conv_b_id}, str(len(ids)))

    print("\n8. rename, pin, archive, restore")
    renamed = api.patch(
        f"/api/chat/conversations/{conv_b_id}",
        json={"title": "دوم"},
        headers=headers_a,
    )
    check("renamed", renamed.json()["title"] == "دوم")
    pinned = api.patch(
        f"/api/chat/conversations/{conv_b_id}",
        json={"pinned": True},
        headers=headers_a,
    )
    check("pinned", pinned.json()["pinned"] is True)
    archived = api.patch(
        f"/api/chat/conversations/{conv_b_id}",
        json={"archived": True},
        headers=headers_a,
    )
    check("archived", archived.json()["archived"] is True)
    open_list = api.get("/api/chat/conversations", headers=headers_a).json()
    check("archived hidden from open list", [item["id"] for item in open_list] == [conv_a_id])
    hidden = api.get(
        "/api/chat/conversations", params={"archived": True}, headers=headers_a
    ).json()
    check("archived list contains it", [item["id"] for item in hidden] == [conv_b_id])
    restored = api.patch(
        f"/api/chat/conversations/{conv_b_id}",
        json={"archived": False},
        headers=headers_a,
    )
    check("restored", restored.json()["archived"] is False)
    after_restore = api.get("/api/chat/conversations", headers=headers_a).json()
    check("restored chat returns to history", conv_b_id in [item["id"] for item in after_restore])

    print("\n9. signed-out list is empty; signed-in list returns")
    check(
        "no token → empty history",
        api.get("/api/chat/conversations").json() == [],
    )
    check(
        "token → history returns",
        conv_a_id in [item["id"] for item in api.get("/api/chat/conversations", headers=headers_a).json()],
    )

    print("\n10. delete persists")
    deleted = api.delete(f"/api/chat/conversations/{conv_b_id}", headers=headers_a)
    check("delete succeeded", deleted.status_code == 204)
    after_delete = api.get("/api/chat/conversations", headers=headers_a).json()
    check("deleted chat gone after reload", conv_b_id not in [item["id"] for item in after_delete])
    missing_deleted = api.get(f"/api/chat/conversations/{conv_b_id}", headers=headers_a)
    check("deleted id is generic 404", missing_deleted.status_code == 404)
    check(
        "deleted copy is generic",
        missing_deleted.json().get("message_fa") == "این گفتگو پیدا نشد.",
    )

    print("\n11. nonexistent id is generic not-found")
    missing = api.get(f"/api/chat/conversations/{uuid.uuid4()}", headers=headers_a)
    check("unknown id is 404", missing.status_code == 404)
    check("unknown copy is generic", missing.json().get("message_fa") == "این گفتگو پیدا نشد.")

    print("\n12. account B cannot open A’s chat or attachment")
    try:
        token_b = signup(plain, auth, anon_key, email_b)
    except RuntimeError:
        return report()
    headers_b = {"Authorization": f"Bearer {token_b}"}
    api.post("/api/session/adopt", headers=headers_b)
    stranger_list = api.get("/api/chat/conversations", headers=headers_b).json()
    check("B’s history is empty", stranger_list == [])
    stranger_get = api.get(f"/api/chat/conversations/{conv_a_id}", headers=headers_b)
    check("B gets generic 404 for A’s chat", stranger_get.status_code == 404)
    check(
        "B’s 404 does not leak title",
        "سلام" not in stranger_get.text and stranger_get.json().get("message_fa") == "این گفتگو پیدا نشد.",
    )
    stranger_resolve = api.post(
        "/api/assets/resolve", json={"paths": [path]}, headers=headers_b
    ).json()
    check("B cannot resolve A’s attachment", stranger_resolve.get(path) is None)

    return report()


def report() -> int:
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
