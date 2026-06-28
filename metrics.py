from prometheus_client import Counter, Histogram, Gauge

# ---------------------------------------------------------------------------
# Request-level SLIs
# ---------------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "lta_proxy_requests_total",
    "Total HTTP requests handled by the proxy",
    ["endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "lta_proxy_request_duration_seconds",
    "End-to-end request latency (seconds)",
    ["endpoint"],
    buckets=[0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ---------------------------------------------------------------------------
# Upstream (LTA DataMall) SLIs
# ---------------------------------------------------------------------------

LTA_UPSTREAM_ERRORS = Counter(
    "lta_upstream_errors_total",
    "Errors returned by or from LTA DataMall upstream",
    ["reason"],  # e.g. timeout, http_502, http_500
)

LTA_UPSTREAM_LATENCY = Histogram(
    "lta_upstream_request_duration_seconds",
    "Latency of calls made to LTA DataMall (seconds)",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ---------------------------------------------------------------------------
# Cache SLIs  (data freshness — the most interesting SLI in this project)
# ---------------------------------------------------------------------------

CACHE_HITS = Counter(
    "lta_cache_hits_total",
    "Requests served from cache without calling LTA",
)

CACHE_MISSES = Counter(
    "lta_cache_misses_total",
    "Requests that required a live LTA call",
)

CACHE_STALE_SERVES = Counter(
    "lta_cache_stale_serves_total",
    "Requests served from stale cache because LTA was unavailable",
)

BUS_ARRIVAL_CACHE_AGE = Gauge(
    "lta_bus_arrival_cache_age_seconds",
    "Age of the most recently served cache entry (seconds). SLO: < 30s",
    ["bus_stop_code"],
)
