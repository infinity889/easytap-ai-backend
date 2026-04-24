import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core import signing


GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
STATE_SALT = "accounts.google-oauth"


class GoogleOAuthError(Exception):
    pass


def _json_request(url: str, *, method: str = "GET", data: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}

    if data is not None:
        body = urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise GoogleOAuthError("Google OAuth request failed.") from exc


def build_google_authorize_url(*, role: str | None = None, next_path: str | None = None) -> str:
    payload = {"role": role or "student", "next": next_path or ""}
    state = signing.dumps(payload, salt=STATE_SALT)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(settings.GOOGLE_OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"


def parse_google_state(value: str) -> dict[str, Any]:
    try:
        return signing.loads(value, salt=STATE_SALT, max_age=600)
    except Exception as exc:
        raise GoogleOAuthError("Invalid Google OAuth state.") from exc


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    return _json_request(
        GOOGLE_TOKEN_URL,
        method="POST",
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )


def fetch_google_userinfo(access_token: str) -> dict[str, Any]:
    request = Request(
        GOOGLE_USERINFO_URL,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="GET",
    )
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise GoogleOAuthError("Failed to fetch Google user profile.") from exc
