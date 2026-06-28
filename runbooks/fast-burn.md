# Runbook: LTAProxyFastBurn

**Alert:** `LTAProxyFastBurn`
**Severity:** Critical
**SLO:** Availability ≥ 99.5%
**Meaning:** The proxy is burning its monthly error budget at >14x the normal rate. At this pace the entire monthly budget is exhausted in ~2 hours.

---

## 1. Confirm the alert is real

```promql
# Current error rate
1 - rate(lta_proxy_requests_total{status="200"}[5m]) / rate(lta_proxy_requests_total[5m])

# Burn rate multiplier
(1 - rate(lta_proxy_requests_total{status="200"}[1h]) / rate(lta_proxy_requests_total[1h])) / 0.005
```

If burn rate < 14, the alert may have already resolved — check Alertmanager.

---

## 2. Identify the error type

```promql
# What status codes are failing?
rate(lta_proxy_requests_total[5m])

# Is LTA upstream the cause?
rate(lta_upstream_errors_total[5m])
```

| Observation | Likely cause |
|-------------|-------------|
| `lta_upstream_errors_total{reason="timeout"}` spiking | LTA DataMall is slow or down |
| `lta_upstream_errors_total{reason="http_502"}` spiking | LTA DataMall is returning errors |
| Proxy returning 5xx but upstream errors = 0 | Bug in proxy code |

---

## 3. Mitigations

**If LTA upstream is down:**
- Stale cache will serve for any stop that has been requested before
- New stops will return 504 — acceptable during an LTA outage
- No action needed unless outage exceeds SLO window

**If proxy is the cause:**
```bash
# Check logs
docker compose logs app --tail=100

# Restart the proxy
docker compose restart app
```

---

## 4. Declare resolved

Alert auto-resolves when burn rate drops below threshold for 2 minutes.
Log a post-mortem if the outage lasted > 30 minutes.
