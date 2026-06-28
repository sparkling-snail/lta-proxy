# Runbook: LTAProxySlowBurn

**Alert:** `LTAProxySlowBurn`
**Severity:** Warning
**SLO:** Availability ≥ 99.5%
**Meaning:** The proxy is burning error budget at >3x the normal rate over 6 hours. Not an emergency, but if left unaddressed ~5% of the monthly budget will be spent today.

---

## 1. Confirm the alert is real

```promql
# 6h burn rate multiplier
(1 - rate(lta_proxy_requests_total{status="200"}[6h]) / rate(lta_proxy_requests_total[6h])) / 0.005
```

Burn rate between 3–14 = slow burn (warning). Above 14 = fast burn (critical, separate alert).

---

## 2. Identify the pattern

```promql
# Error rate over time — is it steady or spiky?
rate(lta_proxy_requests_total{status!="200"}[30m])

# Upstream error breakdown
rate(lta_upstream_errors_total[30m])

# Cache stale serves — are we degraded but not fully down?
rate(lta_cache_stale_serves_total[30m])
```

| Pattern | Interpretation |
|---------|---------------|
| Steady low error rate | Persistent upstream instability — monitor |
| Spiky errors, recovering | Intermittent LTA issues — likely self-resolving |
| High stale serves + low upstream errors | Cache TTL may be too short |

---

## 3. Actions

**No immediate action required** unless burn rate is trending upward toward 14x.

- If errors are LTA-sourced and intermittent: monitor for 30 minutes
- If errors are proxy-sourced: check logs and consider a rolling restart
- If stale serves are high: consider increasing `CACHE_TTL` in `app.py`

---

## 4. Escalation

If burn rate exceeds 14x → `LTAProxyFastBurn` fires automatically. Follow that runbook.
