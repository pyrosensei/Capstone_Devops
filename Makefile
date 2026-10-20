.PHONY: env install run test coverage lint format docker-up docker-down obs-up elk-up sonar-up \
	postgres-up postgres-down db-upgrade kind-up k8s-apply k8s-canary k8s-delete helm-lint smoke

ENV_NAME=capstone_devops

env:
	conda create -n $(ENV_NAME) python=3.11 -y || true
	conda run -n $(ENV_NAME) python -m pip install --upgrade pip
	conda run -n $(ENV_NAME) python -m pip install -r requirements-dev.txt

install:
	conda run -n $(ENV_NAME) python -m pip install -r requirements-dev.txt

run:
	conda run -n $(ENV_NAME) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	conda run -n $(ENV_NAME) pytest

coverage:
	conda run -n $(ENV_NAME) pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml

lint:
	conda run -n $(ENV_NAME) ruff check app tests worker

format:
	conda run -n $(ENV_NAME) ruff format app tests worker

docker-up:
	docker compose up --build -d api worker redis

docker-down:
	docker compose down

obs-up:
	docker compose --profile observability up -d

elk-up:
	docker compose --profile elk up -d

sonar-up:
	docker compose --profile security up -d sonarqube

postgres-up:
	docker compose --profile postgres -f docker-compose.yml -f docker-compose.postgres.yml up --build -d

postgres-down:
	docker compose --profile postgres -f docker-compose.yml -f docker-compose.postgres.yml down

db-upgrade:
	conda run -n $(ENV_NAME) alembic upgrade head

kind-up:
	powershell -File scripts/kind-up.ps1

k8s-apply:
	kubectl apply -k kubernetes/overlays/dev

k8s-canary:
	kubectl apply -k kubernetes/overlays/canary

k8s-delete:
	kubectl delete -k kubernetes/overlays/dev --ignore-not-found

helm-lint:
	helm lint helm/devplane

smoke:
	conda run -n $(ENV_NAME) python scripts/smoke.py
