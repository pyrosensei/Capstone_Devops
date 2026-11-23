# Local Jenkins controller validation

On 23 November 2026, the existing Docker Desktop controller started and its
API reported Jenkins 2.580.1. The `devplane-ci` job existed, but its saved XML
had no Pipeline definition and the API reported no builds. The controller
accepted anonymous reads while listening on all interfaces. It was stopped
after this check.

## Follow-up validation

Follow the [Jenkins setup guide](../jenkins-setup.md) to create an authenticated,
loopback-bound controller and save the `devplane-ci` Pipeline definition before
running it. Record the checked-out commit, the build result, and the lint,
test, Docker build and scan stages in the run evidence.
