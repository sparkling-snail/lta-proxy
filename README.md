# LTA Bus Arrival Proxy — SLO Dashboard

A production-instrumented proxy over the [LTA DataMall Bus Arrival API](https://datamall.lta.gov.sg),
built as a portfolio SRE project demonstrating SLI definition, SLO tracking, burn rate alerting,
and Grafana dashboarding.

## Architecture

```text
Client → FastAPI Proxy → LTA DataMall API
              ↓
         Prometheus ← scrapes /metrics every 10s
              ↓
           Grafana (dashboards + SLO panels)
              ↓
        Alertmanager (burn rate alerts)
```

## SLOs defined

| SLO | Target | SLI |
| --- | ------ | --- |
| Availability | ≥ 99.5% | `successful_requests / total_requests` |
| P95 Latency | < 500ms | `histogram_quantile(0.95, ...)` |
| Data freshness | cache age < 30s | `lta_bus_arrival_cache_age_seconds` |

## Quick start

### 1. Get an LTA API key

Register at [datamall.lta.gov.sg](https://datamall.lta.gov.sg/content/datamall/en/request-for-api.html) (free, ~10 min).

### 2. Configure

```bash
cp .env.example .env
# edit .env and paste your key
```

### 3. Run

```bash
docker compose up --build
```

### 4. Verify

```bash
# Hit the proxy
curl http://localhost:8000/arrivals/83139

# Check metrics are being exported
curl http://localhost:8000/metrics | grep lta_
```

### 5. Open dashboards

- Grafana: <http://localhost:3000> (admin / admin)
- Prometheus: <http://localhost:9090>
- Alertmanager: <http://localhost:9093>

## Key bus stop codes to try

| Stop code | Location |
| --------- | -------- |
| 83139 | Sengkang Bus Interchange |
| 75009 | Tampines Bus Interchange |
| 01012 | Victoria St opp. National Library |
| 65199 | Compassvale Rd |

## Runbooks

- [Fast burn alert](runbooks/fast-burn.md)
- [Slow burn alert](runbooks/slow-burn.md)
- [High latency alert](runbooks/high-latency.md)
- [Stale cache alert](runbooks/stale-cache.md)
