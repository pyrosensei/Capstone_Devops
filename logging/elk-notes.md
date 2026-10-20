# Centralized logging

## Recommended local stack (already in Compose profile `observability`)

- Fluentd receives container forward logs on port 24224 and prints them (swap `@type elasticsearch` when you have an ES node).
- Loki stores log streams; Grafana is provisioned with a Loki datasource.
- Promtail config lives in `logging/loki/promtail-config.yml` for Docker and Kubernetes scrape.

## Full ELK (optional)

```bash
docker run -d --name elasticsearch -p 9200:9200 -e discovery.type=single-node docker.elastic.co/elasticsearch/elasticsearch:8.14.3
docker run -d --name kibana --link elasticsearch -p 5601:5601 docker.elastic.co/kibana/kibana:8.14.3
```

Point Fluentd `match` at Elasticsearch:

```
<match **>
  @type elasticsearch
  host elasticsearch
  port 9200
  logstash_format true
</match>
```

Application logs are JSON via `structlog` (see `app/core/logging.py`), which Kibana/Grafana can parse without extra grok.
