# Jenkins CI setup

## Local Jenkins

```bash
docker run -d --name jenkins -p 8080:8080 -p 50000:50000 ^
  -v jenkins_home:/var/jenkins_home ^
  -v /var/run/docker.sock:/var/run/docker.sock ^
  jenkins/jenkins:lts
```

Install plugins: Pipeline, Git, Docker Pipeline, Credentials Binding, optional SonarQube Scanner, AnsiColor.

Create credentials:

- `github-pat` if using a private repo
- `docker-registry` if pushing images
- `sonar-token` for Phase 9

## Webhook vs polling

- **GitHub webhook**: Jenkins URL `http://<host>:8080/github-webhook/` plus a GitHub personal access token. Requires a reachable Jenkins (or ngrok).
- **SCM polling**: in the job, enable "Poll SCM" with `H/5 * * * *` for classrooms without public URLs.

Connect a Pipeline job to this repository and set Script Path `Jenkinsfile`.

## Windows agents

If the Jenkins agent is Windows, replace `sh` steps with `bat` equivalents, or run the job in a Linux agent / Docker-in-Docker agent.

## SonarQube

```bash
docker run -d --name sonarqube -p 9000:9000 sonarqube:lts-community
```

Set Jenkins env `SONAR_HOST_URL=http://sonarqube:9000` so the optional Sonar stage runs.
