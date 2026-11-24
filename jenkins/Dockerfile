FROM python:3.11-slim-bookworm AS python
FROM docker:29-cli AS docker
FROM jenkins/jenkins:lts-jdk21

USER root
COPY --from=python /usr/local/ /usr/local/
COPY --from=docker /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
USER jenkins

RUN python3 --version && python3 -c "import sqlite3, ssl" && docker buildx version \
    && jenkins-plugin-cli --plugins workflow-aggregator git junit ansicolor timestamper sonar
