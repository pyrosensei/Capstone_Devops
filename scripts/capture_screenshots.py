"""Capture evidence screenshots for the DevPlane capstone.

The script drives real, already-running services with Playwright and writes
PNG files to ``docs/screenshots``. Every target is optional: if a service is
not reachable the script reports it and continues, so the same command works
for a partial environment.

Usage (PowerShell):

    conda run -n capstone_devops python scripts/capture_screenshots.py `
        --devplane-url http://127.0.0.1:8001 `
        --grafana-url http://127.0.0.1:3000 `
        --prometheus-url http://127.0.0.1:9090 `
        --argocd-url https://127.0.0.1:8090

Prerequisites:

    conda run -n capstone_devops pip install playwright
    conda run -n capstone_devops python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "screenshots"


def _log(message: str) -> None:
    print(f"[capture] {message}")


def _shot(page, output_dir: Path, name: str, full_page: bool = True) -> None:
    target = output_dir / name
    page.screenshot(path=str(target), full_page=full_page)
    _log(f"wrote {target.relative_to(REPO_ROOT)}")


def capture_devplane(page, base_url: str, output_dir: Path) -> None:
    page.goto(f"{base_url}/", wait_until="domcontentloaded")
    _shot(page, output_dir, "ui-login.png")

    page.fill("#login-form input[name=email]", "admin@devplane.local")
    page.fill("#login-form input[name=password]", "admin123")
    page.click("#login-form button[type=submit]")
    page.wait_for_selector("#app-panel:not([hidden])", timeout=15000)
    page.wait_for_timeout(1500)
    _shot(page, output_dir, "ui-catalog.png")

    page.click("button[data-tab=delivery]")
    page.wait_for_timeout(1500)
    _shot(page, output_dir, "deployment-history.png")

    page.click("button[data-tab=config]")
    page.wait_for_timeout(1200)
    _shot(page, output_dir, "feature-flags.png")

    page.click("button[data-tab=ops]")
    page.wait_for_timeout(800)
    try:
        page.select_option("#ops-tool", index=0)
        page.fill("#ops-form input[name=pod]", "devplane-api")
        page.fill("#ops-form input[name=namespace]", "devplane")
        page.click("#ops-form button[type=submit]")
        page.wait_for_timeout(2000)
    except PlaywrightError as exc:
        _log(f"ops tool run skipped: {exc}")
    _shot(page, output_dir, "ops-registry.png")

    page.click("button[data-tab=admin]")
    page.wait_for_timeout(1500)
    _shot(page, output_dir, "admin-audit.png")


def capture_grafana(page, base_url: str, output_dir: Path) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.wait_for_selector("input[name=user]", timeout=30000)
    page.fill("input[name=user]", os.environ.get("GRAFANA_USER", "admin"))
    page.fill("input[name=password]", os.environ.get("GRAFANA_PASSWORD", "admin"))
    page.press("input[name=password]", "Enter")
    try:
        page.wait_for_url(lambda url: "/login" not in url, timeout=30000)
    except PlaywrightError:
        page.locator("button:has-text('Log in'), button[type=submit]").first.click()
        page.wait_for_timeout(4000)
    page.goto(f"{base_url}/d/devplane-overview", wait_until="domcontentloaded")
    try:
        page.wait_for_selector("text=DevPlane Control Plane", timeout=30000)
    except PlaywrightError as exc:
        _log(f"grafana dashboard title not found: {exc}")
    page.wait_for_timeout(6000)
    _shot(page, output_dir, "grafana-dashboard.png")


def capture_prometheus(page, base_url: str, output_dir: Path) -> None:
    page.goto(f"{base_url}/targets", wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    _shot(page, output_dir, "prometheus-targets.png")


def capture_argocd(page, base_url: str, output_dir: Path) -> None:
    password = os.environ.get("ARGOCD_ADMIN_PASSWORD", "")
    page.goto(f"{base_url}/", wait_until="domcontentloaded")
    if password:
        page.fill("input[name=username]", "admin")
        page.fill("input[name=password]", password)
        page.click("button[type=submit]")
        page.wait_for_timeout(4000)
    page.goto(f"{base_url}/applications", wait_until="domcontentloaded")
    try:
        page.wait_for_selector("text=devplane", timeout=30000)
    except PlaywrightError as exc:
        _log(f"argocd application row not rendered: {exc}")
    page.wait_for_timeout(4000)
    _shot(page, output_dir, "argocd-applications.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--devplane-url", default="")
    parser.add_argument("--grafana-url", default="")
    parser.add_argument("--prometheus-url", default="")
    parser.add_argument("--argocd-url", default="")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        ("DevPlane UI", args.devplane_url, capture_devplane),
        ("Grafana", args.grafana_url, capture_grafana),
        ("Prometheus", args.prometheus_url, capture_prometheus),
        ("Argo CD", args.argocd_url, capture_argocd),
    ]

    failures = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for name, url, handler in targets:
            if not url:
                _log(f"skipping {name} (no URL given)")
                continue
            context = browser.new_context(
                viewport={"width": 1600, "height": 1000},
                ignore_https_errors=True,
            )
            page = context.new_page()
            try:
                handler(page, url, output_dir)
            except PlaywrightError as exc:
                failures += 1
                _log(f"FAILED {name}: {exc}")
            finally:
                context.close()
        browser.close()

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
