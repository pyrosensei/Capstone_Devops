"""Slack/email notification stub used by CI or webhooks."""

from __future__ import annotations

import json
import os
import urllib.request


def notify(title: str, body: str) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    payload = {"text": f"*{title}*\n{body}"}
    if not webhook:
        print(json.dumps({"channel": "stub", **payload}))
        return
    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=5)


if __name__ == "__main__":
    notify("DevPlane CI", "Pipeline finished (stub).")
