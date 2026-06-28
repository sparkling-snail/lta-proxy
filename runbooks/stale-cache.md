# Runbook: LTAProxyStaleCacheData

**Alert:** `LTAProxyStaleCacheData`
**Severity:** Warning
**SLO:** Data freshness — cache age < 30s
**Meaning:** A bus stop's cached arrival data is older than 30 seconds. Users may be seeing outdated bus times.

---

## 1. Confirm the alert

```promql
# Which stops are stale and by how much?
lta_bus_arrival_cache_age_seconds
```

---

## 2. Understand why

```promql
# Is LTA upstream failing for this stop?
rate(lta_upstream_errors_total[5m])

# Are we serving stale data instead of erroring?
rate(lta_cache_stale_serves_total[5m])
```

If `lta_cache_stale_serves_total` is climbing, it means LTA is down and the proxy is
intentionally serving stale data rather than returning errors. This is **correct behaviour**
— the stale-serve logic is a resilience feature, not a bug.

---

## 3. Actions

**If stale serves are high and LTA is down:**
- This is the intended graceful degradation path
- Monitor LTA availability — it usually recovers within minutes
- No proxy action needed

**If stale serves are zero but cache age is still high:**
- Something is wrong with the cache refresh logic
- Check proxy logs: `docker compose logs app --tail=50`
- Restart: `docker compose restart app`

---

## 4. Resolve

Alert auto-resolves when cache age drops below 30s. This typically happens within
1–2 minutes of LTA coming back online.
