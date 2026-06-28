import time
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from dotenv import load_dotenv

from metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    LTA_UPSTREAM_ERRORS,
    LTA_UPSTREAM_LATENCY,
    CACHE_HITS,
    CACHE_MISSES,
    CACHE_STALE_SERVES,
    BUS_ARRIVAL_CACHE_AGE,
)

load_dotenv()

LTA_API_KEY = os.getenv("LTA_API_KEY", "")
LTA_BASE = "https://datamall2.mytransport.sg/ltaodataservice"
CACHE_TTL = 20          # seconds — LTA refreshes data every ~30s
UPSTREAM_TIMEOUT = 5.0  # seconds

# ---------------------------------------------------------------------------
# Simple in-memory cache  { bus_stop_code: (fetched_at_ts, data) }
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, dict]] = {}


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not LTA_API_KEY:
        print("WARNING: LTA_API_KEY is not set. Set it in your .env file.")
    yield


app = FastAPI(
    title="LTA Bus Arrival Proxy",
    description="Thin proxy over LTA DataMall with Prometheus SLI instrumentation",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount /metrics endpoint for Prometheus to scrape
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ---------------------------------------------------------------------------
# LTA upstream caller
# ---------------------------------------------------------------------------
async def fetch_from_lta(bus_stop_code: str) -> dict:
    """Call LTA DataMall Bus Arrival v3. Raises HTTPException on failure."""
    url = f"{LTA_BASE}/v3/BusArrival"
    headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
    params = {"BusStopCode": bus_stop_code}

    upstream_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
    except httpx.TimeoutException:
        LTA_UPSTREAM_ERRORS.labels(reason="timeout").inc()
        raise HTTPException(504, detail="LTA DataMall timed out")
    except httpx.RequestError as exc:
        LTA_UPSTREAM_ERRORS.labels(reason="connection_error").inc()
        raise HTTPException(502, detail=f"Could not reach LTA: {exc}")
    finally:
        LTA_UPSTREAM_LATENCY.observe(time.time() - upstream_start)

    if resp.status_code != 200:
        LTA_UPSTREAM_ERRORS.labels(reason=f"http_{resp.status_code}").inc()
        raise HTTPException(502, detail=f"LTA returned HTTP {resp.status_code}")

    return resp.json()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/arrivals/{bus_stop_code}", summary="Get real-time bus arrivals")
async def get_arrivals(bus_stop_code: str):
    """
    Returns real-time bus arrival times for the given bus stop code.
    Results are cached for 20 seconds to reduce LTA upstream pressure.
    On upstream failure, stale cache is served if available.

    Example bus stops:
      83139  — Sengkang Bus Interchange
      75009  — Tampines Bus Interchange
      01012  — Victoria St opp. National Library
    """
    start = time.time()
    status_code = "200"

    try:
        now = time.time()
        cached = _cache.get(bus_stop_code)
        cache_age = now - cached[0] if cached else None

        if cached and cache_age is not None and cache_age < CACHE_TTL:
            # Fresh cache hit
            CACHE_HITS.inc()
            BUS_ARRIVAL_CACHE_AGE.labels(bus_stop_code=bus_stop_code).set(cache_age)
            return cached[1]

        # Cache miss — call LTA
        CACHE_MISSES.inc()
        try:
            data = await fetch_from_lta(bus_stop_code)
            _cache[bus_stop_code] = (now, data)
            BUS_ARRIVAL_CACHE_AGE.labels(bus_stop_code=bus_stop_code).set(0)
            return data

        except HTTPException as upstream_err:
            # Upstream failed — serve stale cache if we have it
            if cached:
                CACHE_STALE_SERVES.inc()
                BUS_ARRIVAL_CACHE_AGE.labels(bus_stop_code=bus_stop_code).set(
                    now - cached[0]
                )
                return JSONResponse(
                    content=cached[1],
                    headers={"X-Served-From": "stale-cache"},
                )
            # No cache at all — propagate the error
            status_code = str(upstream_err.status_code)
            raise

    except HTTPException as e:
        status_code = str(e.status_code)
        raise
    finally:
        REQUEST_COUNT.labels(endpoint="arrivals", status=status_code).inc()
        REQUEST_LATENCY.labels(endpoint="arrivals").observe(time.time() - start)


@app.get("/health", summary="Health check")
async def health():
    """Simple liveness probe."""
    REQUEST_COUNT.labels(endpoint="health", status="200").inc()
    return {"status": "ok"}


@app.get("/", summary="API info")
async def root():
    return {
        "service": "LTA Bus Arrival Proxy",
        "endpoints": {
            "arrivals": "/arrivals/{bus_stop_code}",
            "health": "/health",
            "metrics": "/metrics",
        },
        "example": "/arrivals/83139",
    }
