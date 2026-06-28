# Runbook: LTAProxyHighLatency

**Alert:** `LTAProxyHighLatency`
**Severity:** Warning
**SLO:** P95 latency < 500ms
**Meaning:** 95% of requests are taking longer than 500ms over the last 5 minutes.

---

## 1. Confirm the alert

```promql
# Current P95
histogram_quantile(0.95, rate(lta_proxy_request_duration_seconds_bucket{endpoint="arrivals"}[5m]))

# Compare P50 vs P95 — is the tail bad or is overall latency up?
histogram_quantile(0.50, rate(lta_proxy_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(lta_proxy_request_duration_seconds_bucket[5m]))
```

---

## 2. Identify the source

```promql
# Is LTA upstream slow?
histogram_quantile(0.95, rate(lta_upstream_request_duration_seconds_bucket[5m]))

# Is cache hit rate low (forcing more upstream calls)?
rate(lta_cache_hits_total[5m]) / (rate(lta_cache_hits_total[5m]) + rate(lta_cache_misses_total[5m]))
```

| Observation | Cause |
|-------------|-------|
| Upstream P95 also high | LTA DataMall is slow — not much we can do |
| Upstream fast but proxy slow | Proxy overhead, check CPU/memory |
| Low cache hit rate | Many unique bus stops being queried, more upstream calls |

---

## 3. Mitigations

**If LTA upstream is slow:**
- The `UPSTREAM_TIMEOUT = 5.0s` in `app.py` will cap the worst requests
- Consider lowering to 3s if user experience is the priority over completeness

**If cache hit rate is low:**
- Increase `CACHE_TTL` from 20s to 30s in `app.py` (still within LTA refresh window)
- Restart the proxy to apply: `docker compose restart app`

---

## 4. Resolve

Alert auto-resolves when P95 drops below 500ms for 5 minutes.
