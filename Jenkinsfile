pipeline {
  agent any

  parameters {
    string(name: 'IMAGE_REGISTRY', defaultValue: '', description: 'Optional registry, e.g. registry.example.com/team')
    booleanParam(name: 'DEPLOY_TO_K8S', defaultValue: false, description: 'Deploy the built image to the current kubectl context')
    string(name: 'K8S_OVERLAY', defaultValue: 'kubernetes/overlays/dev', description: 'Kustomize overlay to apply')
  }

  environment {
    IMAGE = "devplane-api"
    TAG = "${env.BUILD_NUMBER}"
  }

  options {
    timestamps()
    ansiColor('xterm')
    timeout(time: 45, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
    disableConcurrentBuilds()
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'git rev-parse --short HEAD > .git-short-sha || true'
      }
    }

    stage('Setup Python (conda/pip)') {
      steps {
        sh '''
          set -eux
          if command -v conda >/dev/null 2>&1; then
            . "$(conda info --base)/etc/profile.d/conda.sh"
            conda activate capstone_devops 2>/dev/null || {
              conda create -n capstone_devops python=3.11 -y
              conda activate capstone_devops
            }
            python -m pip install --upgrade pip
            pip install -r requirements-dev.txt
          else
            python3 -m venv .venv
            . .venv/bin/activate
            python -m pip install --upgrade pip
            pip install -r requirements-dev.txt
          fi
        '''
      }
    }

    stage('Lint') {
      steps {
        sh '''
          set -e
          if command -v conda >/dev/null 2>&1; then
            . "$(conda info --base)/etc/profile.d/conda.sh"
            conda activate capstone_devops
          else
            . .venv/bin/activate
          fi
          ruff check app tests worker
        '''
      }
    }

    stage('Tests + coverage') {
      steps {
        sh '''
          set -e
          mkdir -p reports
          if command -v conda >/dev/null 2>&1; then
            . "$(conda info --base)/etc/profile.d/conda.sh"
            conda activate capstone_devops
          else
            . .venv/bin/activate
          fi
          pytest --cov=app --cov-report=term --cov-report=xml --junitxml=reports/junit.xml
        '''
      }
      post {
        always {
          junit testResults: 'reports/junit.xml', allowEmptyResults: true
        }
      }
    }

    stage('SonarQube (optional)') {
      when { expression { return env.SONAR_HOST_URL?.trim() } }
      steps {
        withSonarQubeEnv('SonarQube') {
          sh '''
            if command -v sonar-scanner >/dev/null 2>&1; then
              sonar-scanner \
                -Dsonar.projectKey=devplane \
                -Dsonar.sources=app \
                -Dsonar.tests=tests \
                -Dsonar.python.coverage.reportPaths=coverage.xml
            else
              echo "sonar-scanner not installed; skipping (see docs/jenkins-setup.md)"
            fi
          '''
        }
      }
    }

    stage('Docker build') {
      steps {
        sh '''
          set -eux
          docker build \
            --build-arg BUILDKIT_INLINE_CACHE=1 \
            --cache-from ${IMAGE}:latest \
            -t ${IMAGE}:${TAG} \
            -t ${IMAGE}:latest \
            .
        '''
      }
    }

    stage('Image scan (optional)') {
      steps {
        sh '''
          if command -v trivy >/dev/null 2>&1; then
            trivy image --severity HIGH,CRITICAL --exit-code 0 --no-progress ${IMAGE}:${TAG}
          else
            echo "trivy not installed; skipping image scan"
          fi
        '''
      }
    }

    stage('Push / tag') {
      steps {
        sh '''
          set -eu
          if [ -n "${IMAGE_REGISTRY}" ]; then
            REF="${IMAGE_REGISTRY}/${IMAGE}:${TAG}"
            docker tag ${IMAGE}:${TAG} "${REF}"
            docker push "${REF}"
          else
            echo "No IMAGE_REGISTRY supplied; keeping local tags ${IMAGE}:${TAG} and ${IMAGE}:latest"
          fi
        '''
      }
    }

    stage('Deploy to Kubernetes (optional)') {
      when { expression { return params.DEPLOY_TO_K8S } }
      steps {
        sh '''
          set -eux
          if command -v kind >/dev/null 2>&1 && kind get clusters | grep -qx devplane-kind; then
            kind load docker-image ${IMAGE}:${TAG} --name devplane-kind
            kubectl -n devplane set image deploy/devplane-api api=${IMAGE}:${TAG}
          fi
          kubectl apply -k ${K8S_OVERLAY}
          kubectl -n devplane rollout status deploy/devplane-api --timeout=180s
        '''
      }
    }
  }

  post {
    success {
      sh 'python scripts/notify_stub.py || true'
    }
    failure {
      sh 'python scripts/notify_stub.py || true'
    }
    always {
      archiveArtifacts artifacts: 'coverage.xml, reports/junit.xml', allowEmptyArchive: true
      sh 'docker image prune -f --filter "until=24h" || true'
    }
  }
}
