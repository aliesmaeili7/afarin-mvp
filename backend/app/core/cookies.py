from fastapi import Response

from app.core.config import Settings


def set_anonymous_cookie(response: Response, settings: Settings, token: str) -> None:
    """
    The anonymous token leaves the server only here, and only as an HttpOnly
    cookie. JavaScript can never read it, which is what makes it safe for the
    token to grant access to an unclaimed campaign.

    SameSite=Lax plus the CORS origin allowlist is the CSRF defence, since the
    cookie now rides along automatically on state-changing requests.
    """
    response.set_cookie(
        key=settings.anon_cookie_name,
        value=token,
        max_age=settings.anon_cookie_max_age,
        path=settings.anon_cookie_path,
        domain=settings.anon_cookie_domain,
        secure=settings.anon_cookie_secure,
        httponly=True,
        samesite=settings.anon_cookie_samesite,
    )


def clear_anonymous_cookie(response: Response, settings: Settings) -> None:
    """
    Called after a successful adoption: the token is spent, the account owns the
    campaign, and there is no reason for the browser to keep holding it. Signing
    out later simply mints a fresh session on the next call that needs one.
    """
    response.delete_cookie(
        key=settings.anon_cookie_name,
        path=settings.anon_cookie_path,
        domain=settings.anon_cookie_domain,
        secure=settings.anon_cookie_secure,
        httponly=True,
        samesite=settings.anon_cookie_samesite,
    )
