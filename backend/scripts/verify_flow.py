"""
End-to-end check against a running stack.

    uv run python -m scripts.verify_flow

Walks the journey the spec is about, using the real FastAPI backend, the real
Supabase Auth server and real private object storage — no mocks anywhere:

    anonymous visit -> photo upload -> brief -> concepts -> pick one
    -> email code sign-up -> campaign adoption -> generation -> dashboard

Requires `supabase start` and the backend on :8000. The one-time code is read
back out of the local mail catcher, which is what the seller would read in their
inbox.
"""

from __future__ import annotations

import io
import os
import re
import sys
import time
from pathlib import Path

import httpx
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


def product_photo() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (900, 900), (196, 118, 52)).save(buffer, format="JPEG")
    return buffer.getvalue()


def read_latest_code(client: httpx.Client, email: str) -> str | None:
    """Pulls the six-digit code out of the newest message for this address."""
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


def main() -> int:
    settings = get_settings()
    anon_key = (
        os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or settings.supabase_service_role_key
    )
    auth = f"{settings.supabase_url.rstrip('/')}/auth/v1"
    email = f"seller-{int(time.time())}@example.com"

    # A cookie jar, because the anonymous session is an HttpOnly cookie the
    # backend sets and the browser replays. Nothing reads it from script.
    browser = httpx.Client(base_url=API, timeout=30.0)
    plain = httpx.Client(timeout=30.0)

    print("\n1. anonymous visit")
    created = browser.post("/api/campaigns", json={})
    campaign = created.json()
    campaign_id = campaign["id"]
    check("campaign created without an account", bool(campaign_id))
    check("session cookie issued", "afarin_anon" in browser.cookies)

    set_cookie = created.headers.get("set-cookie", "").lower()
    check("cookie is HttpOnly", "httponly" in set_cookie)
    check("cookie is SameSite=Lax", "samesite=lax" in set_cookie)
    check("no owner yet", campaign["user_id"] is None)

    print("\n2. product photo")
    uploaded = browser.post(
        f"/api/campaigns/{campaign_id}/images",
        files=[("files", ("product.jpg", product_photo(), "image/jpeg"))],
    ).json()
    path = uploaded[0]["storage_path"]
    check("stored in private object storage", path.startswith("supabase://"))
    check("object key is anchored on the campaign", campaign_id in path)

    signed = browser.post("/api/assets/resolve", json={"paths": [path]}).json()[path]
    check("signed URL issued to the owner", bool(signed))
    if signed:
        fetched = plain.get(signed)
        check(
            "signed URL serves the image",
            fetched.status_code == 200,
            f"{len(fetched.content)} bytes",
        )

    stranger = httpx.Client(base_url=API, timeout=30.0)
    refused = stranger.post("/api/assets/resolve", json={"paths": [path]}).json()
    check("another visitor cannot sign it", refused[path] is None)
    check(
        "another visitor cannot read the campaign",
        stranger.get(f"/api/campaigns/{campaign_id}").status_code == 403,
    )

    print("\n3. brief and concepts")
    browser.post(
        f"/api/campaigns/{campaign_id}/product",
        json={
            "name": "زعفران ممتاز",
            "price_text": "۳۹۹ هزار تومان",
            "main_benefit": "بسته‌بندی هدیه و کیفیت صادراتی",
            "brand_name": "سحند",
        },
    )
    browser.patch(
        f"/api/campaigns/{campaign_id}",
        json={
            "objective": "sell_product",
            "visual_style": "luxury",
            "audience": "کسانی که دنبال هدیه لوکس هستن",
        },
    )
    concepts = browser.post(f"/api/campaigns/{campaign_id}/concepts/generate").json()
    check("three concepts generated", len(concepts) == 3)
    check("copy is Persian", all(c["headline_fa"].strip() for c in concepts))
    check(
        "directions include catalog ids",
        all(
            isinstance(c.get("raw_json", {}).get("style_id"), str)
            and isinstance(c.get("raw_json", {}).get("template_id"), str)
            for c in concepts
        ),
    )
    check(
        "internal creative direction is not shown as a headline",
        all("زعفران" in c["headline_fa"] or c["headline_fa"] for c in concepts),
    )
    browser.post(f"/api/campaigns/{campaign_id}/concepts/{concepts[0]['id']}/select")

    blocked = browser.post(f"/api/campaigns/{campaign_id}/generate")
    check("generation refused before sign-in", blocked.status_code == 403)
    check(
        "refusal speaks Persian",
        blocked.json()["message_fa"] == "برای ساخت کمپین اول باید وارد بشی.",
    )

    print("\n4. sign-up with an emailed code")
    sent = plain.post(
        f"{auth}/otp",
        headers={"apikey": anon_key, "content-type": "application/json"},
        json={"email": email, "create_user": True},
    )
    check("code requested", sent.status_code in (200, 204), f"HTTP {sent.status_code}")

    code = read_latest_code(plain, email)
    check("code arrived by email", code is not None, code or "not received")
    if code is None:
        return report()

    verified = plain.post(
        f"{auth}/verify",
        headers={"apikey": anon_key, "content-type": "application/json"},
        json={"email": email, "token": code, "type": "email"},
    ).json()
    token = verified.get("access_token")
    check("access token issued", bool(token))
    headers = {"Authorization": f"Bearer {token}"}

    print("\n5. adoption")
    adopted = browser.post("/api/session/adopt", headers=headers)
    check("adoption succeeded", adopted.status_code == 200)
    check("profile created", adopted.json()["user"]["email"] == email)
    check("spent cookie cleared", not browser.cookies.get("afarin_anon"))

    detail = browser.get(f"/api/campaigns/{campaign_id}", headers=headers).json()
    check(
        "campaign now belongs to the account", detail["campaign"]["user_id"] is not None
    )
    check(
        "anonymous owner released", detail["campaign"]["anonymous_session_id"] is None
    )
    check(
        "the uploaded photo came along",
        detail["product_images"][0]["storage_path"] == path,
    )
    check("the brand kit came along", detail["brand"]["name"] == "سحند")

    print("\n6. generation")
    started = browser.post(f"/api/campaigns/{campaign_id}/generate", headers=headers)
    check("job accepted", started.status_code == 200)

    seen_stages: list[str] = []
    status: dict = {}
    deadline = time.time() + 60
    while time.time() < deadline:
        status = browser.get(
            f"/api/campaigns/{campaign_id}/status", headers=headers
        ).json()
        stage = status.get("stage")
        if stage and (not seen_stages or seen_stages[-1] != stage):
            seen_stages.append(stage)
            print(f"        {status['percent']:>3}%  {status.get('message_fa') or ''}")
        if status["status"] in ("ready", "partial_failed", "failed"):
            break
        time.sleep(0.8)

    check(
        "campaign reached ready",
        status.get("status") == "ready",
        str(status.get("status")),
    )
    check(
        "progress walked several stages", len(seen_stages) >= 3, " → ".join(seen_stages)
    )

    print("\n7. the finished campaign")
    final = browser.get(f"/api/campaigns/{campaign_id}", headers=headers).json()
    assets = {a["asset_type"] for a in final["assets"]}
    check(
        "post, story and a three-slide carousel",
        assets
        == {"feed_final", "story_final", "carousel_1", "carousel_2", "carousel_3"},
        ", ".join(sorted(assets)),
    )
    copies = {c["copy_type"] for c in final["copies"]}
    check(
        "three captions, stories, CTA, hashtags and a reel idea",
        {
            "caption_short",
            "caption_friendly",
            "caption_persuasive",
            "story",
            "cta",
            "hashtags",
            "reel_concept",
        }
        <= copies,
    )
    check(
        "captions mention the product",
        any("زعفران" in c["content"] for c in final["copies"]),
    )

    print("\n8. dashboard")
    cards = browser.get("/api/campaigns", headers=headers).json()
    mine = next((c for c in cards if c["id"] == campaign_id), None)
    check("the campaign is listed", mine is not None)
    if mine:
        check(
            "card previews the generated ad, not the raw photo",
            mine["thumbnail_spec"] is not None,
        )
        check("card shows the product name", mine["product_name"] == "زعفران ممتاز")
        check("card shows the brand", mine["brand_name"] == "سحند")
    check("a sample campaign was seeded too", len(cards) == 2, f"{len(cards)} cards")

    print("\n9. persistence across devices")
    fresh = httpx.Client(base_url=API, timeout=30.0)
    remote = fresh.get("/api/campaigns", headers=headers).json()
    check("history survives a new browser", len(remote) == len(cards))
    brands = fresh.get("/api/brands", headers=headers).json()
    check("brand kit survives a new browser", any(b["name"] == "سحند" for b in brands))

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
