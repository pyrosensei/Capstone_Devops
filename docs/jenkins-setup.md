# Jenkins CI setup

## Pipeline overview

`Jenkinsfile` is a declarative pipeline with these stages:

1. Checkout and short commit SHA.
2. Python setup: activate/create `capstone_devops` when Conda exists, otherwise create `.venv`.
3. Ruff lint.
4. Pytest with coverage, JUnit XML, and archived artifacts.
5. Optional SonarQube scan.
6. Docker build with inline cache.
7. Optional Trivy image scan.
8. Registry push/tag when `IMAGE_REGISTRY` is supplied.
9. Optional Kubernetes deploy when `DEPLOY_TO_K8S` is enabled.
10. Notify stub and prune old images.

Build parameters:

| Parameter | Default | Purpose |
| --- | --- | --- |
| `IMAGE_REGISTRY` | empty | Optional registry prefix; empty keeps local tags |
| `DEPLOY_TO_K8S` | false | Loads the image into kind (if present) and applies the overlay |
| `K8S_OVERLAY` | `kubernetes/overlays/dev` | Kustomize overlay to deploy |

Environment:

- `IMAGE=devplane-api`
- `TAG=${BUILD_NUMBER}`

## Recommended agent

Use a Linux agent with:

- Git
- Python 3.11
- Docker CLI and access to a Docker daemon
- `kubectl` and `kind` for the optional deploy stage
- Optional `sonar-scanner`, `trivy`

A Jenkins controller can run the pipeline if the Docker socket is mounted, but a dedicated agent is cleaner and matches the `sh` steps.

## Local Jenkins in Docker

Linux shell:

```bash
docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts
```

PowerShell:

```powershell
docker run -d --name jenkins -p 8080:8080 -p 50000:50000 `
  -v jenkins_home:/var/jenkins_home `
  -v /var/run/docker.sock:/var/run/docker.sock `
  jenkins/jenkins:lts
```

Mounting the Docker socket gives the Jenkins container control of the host Docker daemon. That is a significant privilege; use only for a local demo.

Get the initial admin password:

```powershell
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open <http://127.0.0.1:8080> and complete the setup wizard.

## Required plugins

- Pipeline
- Git
- Docker Pipeline
- Credentials Binding
- JUnit
- Coverage (optional)
- SonarQube Scanner (optional)
- AnsiColor
- Timestamper

## Job setup

1. Create a Pipeline job.
2. Point SCM at this repository.
3. Set Script Path to `Jenkinsfile`.
4. For a classroom network, enable SCM polling (`H/5 * * * *`) because GitHub cannot reach a local Jenkins.
5. For webhooks, expose Jenkins and use the GitHub webhook URL `http://<host>:8080/github-webhook/`.

## Credentials

Create these only when needed:

- `github-pat` for a private repository.
- `docker-registry` for registry login.
- `sonar-token` for SonarQube.

Use Jenkins Credentials Binding in a real pipeline extension. The current pipeline reads `IMAGE_REGISTRY` as a parameter and does not hard-code credentials.

## SonarQube

Start SonarQube from Compose:

```powershell
docker compose --profile security up -d sonarqube
```

Open <http://127.0.0.1:9000> (default `admin`/`admin` on first login), create a project/token, then configure a Jenkins SonarQube server named `SonarQube` and set `SONAR_HOST_URL` in the job environment.

The pipeline runs `sonar-scanner` only when `SONAR_HOST_URL` is set. If the scanner is missing, it prints a skip message instead of failing.

## Trivy

Install Trivy on the agent. The pipeline runs:

```bash
trivy image --severity HIGH,CRITICAL --exit-code 0 --no-progress ${IMAGE}:${TAG}
```

`--exit-code 0` keeps the demo pipeline green while still printing findings. Change it to `1` if you want the build to fail on HIGH/CRITICAL findings.

## Deploy stage behavior

When `DEPLOY_TO_K8S` is true:

1. If kind and the `devplane-kind` cluster exist, the image is loaded into kind and the Deployment image is updated.
2. `kubectl apply -k ${K8S_OVERLAY}` runs.
3. The API rollout is awaited.

This assumes Jenkins can reach the target kubeconfig. Do not point it at a shared cluster without review.

## Windows agents

The pipeline uses `sh`. On Windows, run Jenkins in a Linux container/agent or rewrite the steps with `bat`/PowerShell. The application and Docker/kind commands work on Windows; the shell syntax is the only incompatibility.

## Troubleshooting

- **`ruff: command not found`**: `requirements-dev.txt` must be installed in the activated environment. Re-run the setup stage.
- **Docker permission denied**: the Jenkins user is not in the Docker group or the socket is not mounted.
- **Coverage/JUnit missing**: check the `reports/` directory and the pytest exit code.
- **Deploy fails on `kind load`**: the agent cannot see the host's kind cluster. Run Jenkins on the same Docker host or use a registry.
- **Sonar stage skipped**: `SONAR_HOST_URL` is empty or `sonar-scanner` is missing.
