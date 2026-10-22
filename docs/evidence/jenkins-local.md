# Local Jenkins controller (reproducible recipe)

The Jenkinsfile was exercised against a real Jenkins controller running on the
same machine. This is the recipe that was used, so it can be repeated.

## 1. Controller

```powershell
docker run -d --name devplane-jenkins `
  -p 8082:8080 -p 50000:50000 `
  -v devplane_jenkins_home:/var/jenkins_home `
  -v /var/run/docker.sock:/var/run/docker.sock `
  -e JAVA_OPTS="-Djenkins.install.runSetupWizard=false" `
  -e JENKINS_ADMIN_ID=admin -e JENKINS_ADMIN_PASSWORD=admin `
  -e JENKINS_PLUGINS="git workflow-aggregator junit credentials-binding" `
  jenkins/jenkins:lts-jdk21
```

Notes that cost time during the first attempt:

- The `JENKINS_PLUGINS` list is only installed on the **first** start of a
  fresh `JENKINS_HOME`. If the volume already exists, install the plugins
  manually:

  ```bash
  docker exec -u root devplane-jenkins \
    /opt/java/openjdk/bin/java -jar /opt/jenkins-plugin-manager.jar \
    --plugins 'git workflow-aggregator junit credentials-binding' --latest false
  ```

  `java` is not on `PATH` inside the image; it lives in `/opt/java/openjdk/bin`.
- On Docker Desktop the Linux socket path must be used
  (`-v /var/run/docker.sock:/var/run/docker.sock`). The Windows named pipe
  form creates an empty directory instead of the socket. The socket is owned
  by `root`, so also run `chmod 666 /var/run/docker.sock` inside the container.
- The controller needs its own URL, otherwise the CLI refuses to talk to it.
  Write `/var/jenkins_home/jenkins.model.JenkinsLocationConfiguration.xml`
  with `<jenkinsUrl>http://127.0.0.1:8080/</jenkinsUrl>` and restart.

## 2. Pipeline job

The job is created through the Jenkins UI with Playwright
(`scripts/jenkins_create_job.py`), because the job XML that Jenkins writes for
"Pipeline script from SCM" is not reproduced reliably by hand:

```powershell
conda run -n capstone_devops python scripts/jenkins_create_job.py `
    --jenkins-url http://127.0.0.1:8082 `
    --scm-url git://localhost:9418/devplane --branch main --job-name devplane-ci
```

The Git remote is served by `git daemon` inside the controller:

```bash
docker exec -u root devplane-jenkins bash -lc \
  "git daemon --reuseaddr --base-path=/opt --export-all --port=9418 --detach --pid-file=/tmp/gitd.pid"
```

`/opt/devplane` is a snapshot of this repository (committed inside the
container) so the pipeline builds exactly the current working tree.

## 3. Status

- The controller starts, the plugins load and a Pipeline job can be created
  and pointed at the repository.
- A full green run of the pipeline (lint -> tests -> Docker build -> scan)
  is the next step; it was paused because Docker was unavailable in the
  session in which the controller was set up.
- The console output of the run should be archived in
  `docs/evidence/jenkins-console.txt` and the build page captured as
  `docs/screenshots/jenkins-pipeline.png`.
