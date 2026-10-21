# Observability and logging

## Metrics

The API exposes Prometheus text format at `GET /metrics`.

| Metric | Type | Labels | Meaning |
| --- | --- | --- | --- |
| `devplane_http_requests_total` | Counter | `method`, `path`, `status` | HTTP requests by templated route |
| `devplane_http_request_duration_seconds` | Histogram | `method`, `path` | Request latency |
| `devplane_deployments_total` | Counter | `status`, `strategy` | Deployment outcomes |
| `devplane_services` | Gauge | - | Catalog services |
| `devplane_environments` | Gauge | `status` | Environments by state |
| `devplane_active_users` | Gauge | - | Active users |

Business gauges are recomputed from the database at startup and on refresh. Route paths are templated before being used as labels to prevent unbounded cardinality.

Health endpoints:

- `/health/live` - process liveness.
- `/health/ready` - database readiness.
- `/health` - database plus Redis status.

All responses include `X-Request-ID` and `X-Response-Time-ms`. JSON logs include the same request ID.

## Prometheus and Grafana

Start the stack:

```powershell
docker compose up -d api worker redis
docker compose --profile observability up -d
```

Endpoints:

- Prometheus: <http://127.0.0.1:9090>
- Grafana: <http://127.0.0.1:3000>
- Loki: <http://127.0.0.1:3100>

Grafana provisioning is stored in:

- `monitoring/grafana/provisioning/datasources/datasource.yml`
- `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- `monitoring/grafana/dashboards/devplane.json`

The dashboard uses the Prometheus datasource UID `prometheus` and the Loki datasource UID `loki`.

Prometheus scrapes `api:8000` inside Compose. A second target, `host.docker.internal:8000`, supports a Prometheus container watching a host-run API.

Useful queries:

```promql
sum(rate(devplane_http_requests_total[5m])) by (status)
histogram_quantile(0.95, sum(rate(devplane_http_request_duration_seconds_bucket[5m])) by (le))
devplane_environments
devplane_deployments_total
```

## Alerts

`monitoring/alert-rules.yml` defines:

- API scrape target down.
- 5xx error rate above 5%.
- p95 latency above 1 second.
- Any failed deployment in 15 minutes.
- More than three environments stuck provisioning.

Alertmanager is not included. Wire these rules to an Alertmanager instance or Grafana alerting for notification delivery.

## Logs with Loki

The `observability` profile starts:

- `loki` with `logging/loki/loki-config.yml`.
- `promtail` with `logging/loki/promtail-config.yml`.
- Promtail reads Docker container logs through the Docker socket.

In Grafana, select the Loki datasource and query labels such as `{container="devplane-api"}`.

The application writes structured JSON logs. The request ID makes it possible to correlate an HTTP response with server-side events.

## ELK alternative

```powershell
docker compose --profile elk up -d
```

- Elasticsearch: <http://127.0.0.1:9200>
- Kibana: <http://127.0.0.1:5601>
- Logstash Beats input: port 5000; monitoring API: port 9600

Pipeline: `logging/elk/logstash.conf`. The stack is heavy; allocate at least 6 GB to Docker.

## Fluentd alternative

```powershell
docker compose --profile fluentd up -d fluentd
```

Configuration: `logging/fluentd/fluent.conf`. This profile exposes the forward port 24224 and is intended for demonstrating the Fluentd variant of the logging phase.

## Kubernetes observability

The manifests expose metrics through the existing API Service. To scrape them in-cluster you would add a ServiceMonitor/PodMonitor (Prometheus Operator) or a scrape config targeting `devplane-api.devplane.svc:80`. The Compose Prometheus setup is the validated path.

For quick checks:

```powershell
kubectl -n devplane logs deploy/devplane-api --tail=100
kubectl -n devplane port-forward svc/devplane-api 8001:80
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8001/metrics
```

## Validation checklist

Validated locally against the `observability` profile:

1. `docker compose ps` shows API, worker, and Redis healthy — verified.
2. Prometheus targets `devplane-api` and `devplane-host` are `UP` — verified.
3. Grafana shows the provisioned `DevPlane` dashboard and both datasources — verified.
4. Loki returns `devplane-api` container logs — verified.
5. Trigger a deployment and observe request/deployment metrics change.
6. Confirm `/health/ready` returns 200 and `/metrics` contains `devplane_http_requests_total`.
