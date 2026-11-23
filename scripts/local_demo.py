"""Run DevPlane on loopback with a fresh SQLite database for the session."""

import argparse
import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from app.db.session import reset_engine


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    with TemporaryDirectory(prefix="devplane-demo-") as directory:
        original_directory = Path.cwd()
        # The temporary working directory keeps the repository's .env and data out of the demo.
        os.chdir(directory)
        os.environ.update(
            APP_ENV="development",
            DATABASE_URL="sqlite:///./data/devplane.db",
            DEMO_MODE="true",
            SECRET_KEY=secrets.token_urlsafe(48),
            BOOTSTRAP_ADMIN_EMAIL="admin@devplane.local",
            BOOTSTRAP_ADMIN_PASSWORD="admin123",
            BOOTSTRAP_DEV_EMAIL="dev@devplane.local",
            BOOTSTRAP_DEV_PASSWORD="dev123",
            REDIS_URL="",
            KUBECONFIG=str(Path(directory) / "kubeconfig"),
            JENKINS_USER="",
            JENKINS_TOKEN="",
            TERRAFORM_STATE_DIR=directory,
            PROVISIONING_DELAY_SECONDS="1",
        )

        try:
            uvicorn.run("app.main:app", host="127.0.0.1", port=args.port)
        finally:
            reset_engine()
            os.chdir(original_directory)


if __name__ == "__main__":
    main()
