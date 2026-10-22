"""Create the DevPlane pipeline job in a local Jenkins and start a build.

The script drives the Jenkins UI with Playwright so that Jenkins itself writes
the job configuration (Pipeline script from SCM -> Git). It is used to produce
the CI evidence for the capstone report.

The Jenkins controller runs in Docker; the Git remote is served inside the
controller by ``git daemon`` (see docs/jenkins-setup.md).

Usage:

    conda run -n capstone_devops python scripts/jenkins_create_job.py \
        --jenkins-url http://127.0.0.1:8082 \
        --scm-url git://localhost:9418/devplane \
        --branch main \
        --job-name devplane-ci
"""

from __future__ import annotations

import argparse
import sys

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

PIPELINE_MODE = "org.jenkinsci.plugins.workflow.job.WorkflowJob"


def _select_scm_definition(page) -> None:
    select = page.locator("select").filter(
        has=page.locator("option", has_text="Pipeline script from SCM")
    )
    if not select.count():
        raise RuntimeError("could not find the Pipeline definition selector")
    option = select.first.locator("option", has_text="Pipeline script from SCM").first
    select.first.select_option(option.get_attribute("value"))
    page.wait_for_timeout(2000)


def _select_git(page) -> None:
    git_radio = page.locator(
        "input[type=radio][id*='git' i], input[type=radio][value*='git' i], "
        "input[type=radio][name*='git' i]"
    )
    if git_radio.count():
        git_radio.first.check(force=True)
    else:
        page.get_by_text("Git", exact=True).first.click(force=True)
    page.wait_for_timeout(2000)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jenkins-url", default="http://127.0.0.1:8082")
    parser.add_argument("--scm-url", default="git://localhost:9418/devplane")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--job-name", default="devplane-ci")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()
        try:
            page.goto(f"{args.jenkins_url}/login", wait_until="domcontentloaded")
            page.fill("#j_username", args.user)
            page.fill("#j_password", args.password)
            page.click("button[type=submit], .btn-primary")
            page.wait_for_timeout(3000)

            page.goto(f"{args.jenkins_url}/view/all/newJob", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            page.fill("#name", args.job_name)
            page.locator(f"input[name=mode][value='{PIPELINE_MODE}']").check(force=True)
            page.get_by_text("OK", exact=True).first.click(force=True)
            page.wait_for_timeout(3500)

            _select_scm_definition(page)
            _select_git(page)

            textareas = page.locator("textarea:visible")
            textareas.last.fill(args.scm_url)
            branch = page.locator("input[type=text]:visible")
            branch.last.fill(f"*/{args.branch}")
            page.wait_for_timeout(500)

            page.get_by_text("Save", exact=True).first.click(force=True)
            page.wait_for_timeout(4000)
            print(f"created job {args.job_name}")

            page.goto(
                f"{args.jenkins_url}/job/{args.job_name}", wait_until="domcontentloaded"
            )
            page.wait_for_timeout(2000)
            page.get_by_text("Build Now", exact=True).first.click(force=True)
            page.wait_for_timeout(5000)
            print("build triggered")
        except PlaywrightError as exc:
            print(f"FAILED: {exc}", file=sys.stderr)
            return 1
        finally:
            context.close()
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
