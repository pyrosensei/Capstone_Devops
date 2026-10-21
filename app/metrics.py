from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "devplane_http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "devplane_http_request_duration_seconds",
    "Request latency",
    ["method", "path"],
)
DEPLOYMENTS_TOTAL = Counter(
    "devplane_deployments_total",
    "Deployments triggered",
    ["status", "strategy"],
)
SERVICES_GAUGE = Gauge("devplane_services", "Catalog services count")
ENVIRONMENTS_GAUGE = Gauge("devplane_environments", "Environments count", ["status"])
ACTIVE_USERS = Gauge("devplane_active_users", "Active users")


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
