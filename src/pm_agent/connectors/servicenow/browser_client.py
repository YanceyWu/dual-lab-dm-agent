from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

from pm_agent.config import settings


def _default_edge_profile(
    platform_name: str,
    home: Path,
    local_app_data: str | None,
) -> Path:
    if platform_name.startswith("win"):
        root = Path(local_app_data).expanduser() if local_app_data else (home / "AppData/Local")
        return root / "Microsoft/Edge/User Data"
    if platform_name == "darwin":
        return home / "Library/Application Support/Microsoft Edge"
    return home / ".config/microsoft-edge"


def _report_urls() -> tuple[str, str]:
    base_url = settings.snow_base_url.strip().rstrip("/")
    report_id = settings.snow_report_id.strip()
    if not base_url or not report_id:
        raise RuntimeError(
            "ServiceNow browser download requires SNOW_BASE_URL and "
            "SNOW_REPORT_ID in local configuration."
        )
    direct_url = f"/sys_report_template.do?jvar_report_id={quote(report_id)}&CSV"
    navigation_target = quote(direct_url.lstrip("/"), safe="")
    return (
        f"{base_url}/now/nav/ui/classic/params/target/{navigation_target}",
        direct_url,
    )


def default_browser_profile() -> Path:
    if settings.snow_browser_profile:
        return Path(settings.snow_browser_profile).expanduser()
    return _default_edge_profile(sys.platform, Path.home(), os.getenv("LOCALAPPDATA"))


def playwright_status() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return False, "Playwright is not installed."
    return True, "ready"


def download_change_request_csv(save_path: Path) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for `pm cr sync`. Install it with "
            "`pip install playwright && python3 -m playwright install chromium`."
        ) from exc

    report_url, direct_csv_url = _report_urls()
    edge_profile = default_browser_profile()
    if not edge_profile.exists():
        raise RuntimeError(
            f"Edge profile not found at {edge_profile}. "
            "Log into ServiceNow in Edge or set SNOW_BROWSER_PROFILE."
        )

    save_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(edge_profile),
            channel="msedge",
            headless=True,
            accept_downloads=True,
        )
        page = context.new_page()
        try:
            page.goto(report_url, wait_until="domcontentloaded", timeout=20000)
            csv_content = page.evaluate(
                """async (directUrl) => {
                    const response = await fetch(directUrl);
                    if (!response.ok) throw new Error('HTTP ' + response.status);
                    return await response.text();
                }""",
                direct_csv_url,
            )
        finally:
            context.close()

    save_path.write_text(csv_content, encoding="utf-8")
    return max(len(csv_content.strip().splitlines()) - 1, 0)
