# Local Jenkins controller validation

On 24 November 2026, an authenticated, loopback-bound Jenkins 2.580.1
controller ran `devplane-ci #3` successfully. The Pipeline-from-SCM job
checked out [bfd1201](https://github.com/pyrosensei/Capstone_Devops/commit/bfd120198b3b34690ee0350078f9bfe731bbd6a8).
An anonymous request to the controller's API returned HTTP 403.

| Stage | Result |
| --- | --- |
| Checkout and setup | GitHub checkout and Python 3.11 environment succeeded. |
| Ruff and pytest | Ruff passed. All 43 tests passed with 93% application coverage. |
| Reports | Jenkins published JUnit results and archived `reports/junit.xml` and `coverage.xml`. |
| Docker | Buildx produced `devplane-api:3` and `devplane-api:latest`. |
| Registry push | The pipeline kept the local tags because no registry was configured. |
| SonarQube, Trivy, and Kubernetes | Skipped. SonarQube and Kubernetes deployment were disabled, and the agent had no Trivy installation. |

The exact `devplane-api:3` image also passed a separate loopback HTTP smoke
test. This verified readiness, two simulated releases, rollback, audit, and
the authenticated metrics scrape.

The previous Docker Desktop job had no saved Pipeline definition or builds.
In the isolated controller, build #2 reached the tagging stage and failed
because Jenkins had yet to export the optional `IMAGE_REGISTRY` parameter.
Build #3 repeated the first-run configuration with the fix and completed
without registry credentials.

Reproduce the run using the [Jenkins setup guide](../jenkins-setup.md).
