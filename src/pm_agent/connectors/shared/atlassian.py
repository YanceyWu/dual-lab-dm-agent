from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from pm_agent.config import PROJECT_ROOT, settings

OAUTH_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
OAUTH_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
REPO_TOKEN_PATH = PROJECT_ROOT / ".auth" / "atlassian" / "tokens.json"
TOKEN_PATHS = [
    REPO_TOKEN_PATH,
]
ENV_PATHS = [
    PROJECT_ROOT / ".env",
]


class AtlassianAuthError(RuntimeError):
    """Raised when Atlassian auth is not configured or cannot be refreshed."""


@dataclass(frozen=True)
class AtlassianAuthSession:
    session: requests.Session
    base_url: str
    auth_type: str
    cloud_id: str | None = None
    token_source: str | None = None


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if raw and not raw.startswith("#") and "=" in raw:
            key, _, value = raw.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _merged_env() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in ENV_PATHS:
        merged.update(_read_env_file(path))
    merged.update({key: value for key, value in os.environ.items() if value})
    return merged


def _env_value(*keys: str) -> str:
    env = _merged_env()
    for key in keys:
        value = env.get(key, "")
        if value:
            return value
    return ""


def _load_tokens() -> tuple[dict, Path | None]:
    for path in TOKEN_PATHS:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8")), path
    return {}, None


def _save_tokens(tokens: dict) -> Path:
    REPO_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPO_TOKEN_PATH.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    return REPO_TOKEN_PATH


def _is_token_expired(tokens: dict, buffer_seconds: int = 300) -> bool:
    obtained_at = float(tokens.get("obtained_at") or 0)
    expires_in = int(tokens.get("expires_in") or 0)
    if not obtained_at or not expires_in:
        return False
    return time.time() > (obtained_at + expires_in - buffer_seconds)


def _refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    verify_ssl: bool,
) -> dict:
    response = requests.post(
        OAUTH_TOKEN_URL,
        json={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        timeout=20,
        verify=verify_ssl,
    )
    response.raise_for_status()
    payload = response.json()
    payload["obtained_at"] = time.time()
    return payload


def _fetch_accessible_resources(access_token: str, verify_ssl: bool) -> list[dict]:
    response = requests.get(
        OAUTH_RESOURCES_URL,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=20,
        verify=verify_ssl,
    )
    response.raise_for_status()
    return response.json()


def _resolve_cloud_id(resources: list[dict], base_url: str, explicit_cloud_id: str) -> str:
    if explicit_cloud_id:
        return explicit_cloud_id
    if not resources:
        raise AtlassianAuthError(
            "No accessible Atlassian resources found. Re-authenticate or configure ATLASSIAN_CLOUD_ID."
        )
    hostname = urlparse(base_url).hostname or ""
    for resource in resources:
        resource_host = urlparse(resource.get("url", "")).hostname or ""
        if hostname and resource_host and (hostname in resource_host or resource_host in hostname):
            return resource["id"]
    if len(resources) == 1:
        return resources[0]["id"]
    raise AtlassianAuthError(
        "Multiple Atlassian sites found. Set ATLASSIAN_CLOUD_ID, JIRA_CLOUD_ID, or CONFLUENCE_CLOUD_ID."
    )


def _probe_path(product: str) -> str:
    if product == "jira":
        return "/rest/api/3/myself"
    if product == "confluence":
        return "/wiki/rest/api/user/current"
    raise AtlassianAuthError(f"Unsupported Atlassian product: {product}")


def _build_oauth_session(
    product: str,
    base_url_hint: str,
    verify_ssl: bool,
    explicit_cloud_id: str,
    client_id: str,
    client_secret: str,
    refresh_token_hint: str,
    tokens: dict,
    token_source: Path | None,
) -> AtlassianAuthSession:
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token") or refresh_token_hint

    if not access_token and refresh_token and client_id and client_secret:
        refreshed = _refresh_access_token(client_id, client_secret, refresh_token, verify_ssl)
        refreshed.setdefault("refresh_token", refresh_token)
        refreshed["accessible_resources"] = _fetch_accessible_resources(
            refreshed["access_token"],
            verify_ssl,
        )
        tokens.update(refreshed)
        token_source = _save_tokens(tokens)
        access_token = tokens["access_token"]

    if not access_token:
        raise AtlassianAuthError(
            "No Atlassian OAuth access token found. Populate .auth/atlassian/tokens.json "
            "or copy an existing token bundle into the repo."
        )

    if _is_token_expired(tokens) and refresh_token and client_id and client_secret:
        refreshed = _refresh_access_token(client_id, client_secret, refresh_token, verify_ssl)
        refreshed.setdefault("refresh_token", refresh_token)
        refreshed["accessible_resources"] = _fetch_accessible_resources(
            refreshed["access_token"],
            verify_ssl,
        )
        tokens.update(refreshed)
        token_source = _save_tokens(tokens)
        access_token = tokens["access_token"]

    resources = tokens.get("accessible_resources") or _fetch_accessible_resources(access_token, verify_ssl)
    tokens["accessible_resources"] = resources
    if token_source is not None:
        token_source = _save_tokens(tokens)

    cloud_id = _resolve_cloud_id(resources, base_url_hint, explicit_cloud_id)
    oauth_base_url = f"https://api.atlassian.com/ex/{product}/{cloud_id}"

    session = requests.Session()
    session.verify = verify_ssl
    session.headers.update(
        {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    probe = session.get(f"{oauth_base_url}{_probe_path(product)}", timeout=20)
    if probe.status_code == 401 and refresh_token and client_id and client_secret:
        refreshed = _refresh_access_token(client_id, client_secret, refresh_token, verify_ssl)
        refreshed.setdefault("refresh_token", refresh_token)
        refreshed["accessible_resources"] = _fetch_accessible_resources(
            refreshed["access_token"],
            verify_ssl,
        )
        tokens.update(refreshed)
        token_source = _save_tokens(tokens)
        session.headers["Authorization"] = f"Bearer {tokens['access_token']}"
        probe = session.get(f"{oauth_base_url}{_probe_path(product)}", timeout=20)

    probe.raise_for_status()
    resolved_token_source = token_source
    if resolved_token_source is None and REPO_TOKEN_PATH.exists():
        resolved_token_source = REPO_TOKEN_PATH
    return AtlassianAuthSession(
        session=session,
        base_url=oauth_base_url,
        auth_type="oauth",
        cloud_id=cloud_id,
        token_source=str(resolved_token_source.resolve()) if resolved_token_source else None,
    )


def get_auth_session(
    product: str,
    *,
    base_url_hint: str,
    email: str = "",
    api_token: str = "",
    verify_ssl: bool = True,
    cloud_id_hint: str = "",
) -> AtlassianAuthSession:
    base_url = base_url_hint.rstrip("/")
    if not base_url:
        raise AtlassianAuthError("Connector base URL is required.")

    tokens, token_source = _load_tokens()
    client_id = settings.atlassian_client_id or _env_value("ATLASSIAN_CLIENT_ID", "JIRA_OAUTH_CLIENT_ID")
    client_secret = settings.atlassian_client_secret or _env_value(
        "ATLASSIAN_CLIENT_SECRET",
        "JIRA_OAUTH_CLIENT_SECRET",
    )
    refresh_token = settings.atlassian_refresh_token or _env_value(
        "ATLASSIAN_REFRESH_TOKEN",
        "JIRA_OAUTH_REFRESH_TOKEN",
    )
    explicit_cloud_id = cloud_id_hint or _env_value(
        "ATLASSIAN_CLOUD_ID",
        "JIRA_CLOUD_ID",
        "CONFLUENCE_CLOUD_ID",
    )

    if tokens or (client_id and client_secret and refresh_token):
        return _build_oauth_session(
            product,
            base_url,
            verify_ssl,
            explicit_cloud_id,
            client_id,
            client_secret,
            refresh_token,
            tokens,
            token_source,
        )

    if email and api_token:
        session = requests.Session()
        session.verify = verify_ssl
        session.auth = (email, api_token)
        session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        probe = session.get(f"{base_url}{_probe_path(product)}", timeout=20)
        probe.raise_for_status()
        return AtlassianAuthSession(
            session=session,
            base_url=base_url,
            auth_type="basic",
            cloud_id=None,
            token_source=None,
        )

    raise AtlassianAuthError(
        "No usable Atlassian auth found. Provide repo-local OAuth tokens "
        "or configure JIRA_USER_EMAIL/JIRA_API_TOKEN in `.env`."
    )
