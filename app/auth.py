"""Simple shared-password auth.

Single password in env, signed-cookie session via Starlette's SessionMiddleware,
auth gate as middleware so all routes are protected by default.
"""
import secrets
from fastapi import Request
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings

# 365 days — "don't make me log in again"
SESSION_MAX_AGE = 60 * 60 * 24 * 365

# Paths that don't require auth
_PUBLIC_PATHS = {"/login", "/logout"}
_PUBLIC_PREFIXES = ("/static/",)


def password_matches(submitted: str) -> bool:
    """Constant-time compare against the configured password."""
    return secrets.compare_digest(
        submitted.encode("utf-8"),
        settings.APP_PASSWORD.encode("utf-8"),
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated requests except for login/logout/static."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in _PUBLIC_PATHS or path.startswith(_PUBLIC_PREFIXES):
            return await call_next(request)

        if request.session.get("authed"):
            return await call_next(request)

        # htmx requests need a special header to trigger a real navigation,
        # otherwise the login page would get swapped into a fragment target.
        if request.headers.get("HX-Request") == "true":
            resp = Response(status_code=401)
            resp.headers["HX-Redirect"] = "/login"
            return resp

        return RedirectResponse("/login", status_code=303)
