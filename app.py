import time
import os
import json
import logging
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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
CACHE_TTL = 20
UPSTREAM_TIMEOUT = 5.0

# ---------------------------------------------------------------------------
# Structured JSON logger — writes to stdout AND /app/logs/app.log
# Logstash reads the log file; stdout is for `docker compose logs`
# ---------------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            entry.update(record.extra)
        return json.dumps(entry)

os.makedirs("/app/logs", exist_ok=True)

logger = logging.getLogger("lta-proxy")
logger.setLevel(logging.INFO)

_fmt = JSONFormatter()

_stdout_handler = logging.StreamHandler()
_stdout_handler.setFormatter(_fmt)

_file_handler = logging.FileHandler("/app/logs/app.log")
_file_handler.setFormatter(_fmt)

logger.addHandler(_stdout_handler)
logger.addHandler(_file_handler)

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
        logger.warning("LTA_API_KEY is not set. Set it in your .env file.")
    else:
        logger.info("LTA proxy starting", extra={"extra": {"api_key_set": True}})
    yield
    logger.info("LTA proxy shutting down")


app = FastAPI(
    title="LTA Bus Arrival Proxy",
    description="Thin proxy over LTA DataMall with Prometheus SLI instrumentation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Mount /metrics endpoint for Prometheus to scrape
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ---------------------------------------------------------------------------
# LTA upstream caller
# ---------------------------------------------------------------------------
async def fetch_from_lta(bus_stop_code: str) -> dict:
    url = f"{LTA_BASE}/v3/BusArrival"
    headers = {"AccountKey": LTA_API_KEY, "accept": "application/json"}
    params = {"BusStopCode": bus_stop_code}

    upstream_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
    except httpx.TimeoutException:
        LTA_UPSTREAM_ERRORS.labels(reason="timeout").inc()
        logger.error("LTA upstream timeout", extra={"extra": {"bus_stop_code": bus_stop_code, "error": "timeout"}})
        raise HTTPException(504, detail="LTA DataMall timed out")
    except httpx.RequestError as exc:
        LTA_UPSTREAM_ERRORS.labels(reason="connection_error").inc()
        logger.error("LTA upstream connection error", extra={"extra": {"bus_stop_code": bus_stop_code, "error": str(exc)}})
        raise HTTPException(502, detail=f"Could not reach LTA: {exc}")
    finally:
        LTA_UPSTREAM_LATENCY.observe(time.time() - upstream_start)

    if resp.status_code != 200:
        LTA_UPSTREAM_ERRORS.labels(reason=f"http_{resp.status_code}").inc()
        logger.error("LTA upstream error", extra={"extra": {"bus_stop_code": bus_stop_code, "lta_status": resp.status_code}})
        raise HTTPException(502, detail=f"LTA returned HTTP {resp.status_code}")

    return resp.json()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/arrivals/{bus_stop_code}", summary="Get real-time bus arrivals")
async def get_arrivals(bus_stop_code: str):
    start = time.time()
    status_code = "200"
    cache_result = "miss"

    try:
        now = time.time()
        cached = _cache.get(bus_stop_code)
        cache_age = now - cached[0] if cached else None

        if cached and cache_age is not None and cache_age < CACHE_TTL:
            CACHE_HITS.inc()
            BUS_ARRIVAL_CACHE_AGE.labels(bus_stop_code=bus_stop_code).set(cache_age)
            cache_result = "hit"
            return cached[1]

        CACHE_MISSES.inc()
        try:
            data = await fetch_from_lta(bus_stop_code)
            _cache[bus_stop_code] = (now, data)
            BUS_ARRIVAL_CACHE_AGE.labels(bus_stop_code=bus_stop_code).set(0)
            return data

        except HTTPException as upstream_err:
            if cached:
                CACHE_STALE_SERVES.inc()
                BUS_ARRIVAL_CACHE_AGE.labels(bus_stop_code=bus_stop_code).set(now - cached[0])
                cache_result = "stale"
                return JSONResponse(
                    content=cached[1],
                    headers={"X-Served-From": "stale-cache"},
                )
            status_code = str(upstream_err.status_code)
            raise

    except HTTPException as e:
        status_code = str(e.status_code)
        raise
    finally:
        duration_ms = round((time.time() - start) * 1000, 2)
        REQUEST_COUNT.labels(endpoint="arrivals", status=status_code).inc()
        REQUEST_LATENCY.labels(endpoint="arrivals").observe(time.time() - start)
        logger.info(
            "request",
            extra={"extra": {
                "path": f"/arrivals/{bus_stop_code}",
                "bus_stop_code": bus_stop_code,
                "status": status_code,
                "duration_ms": duration_ms,
                "cache": cache_result,
            }},
        )


@app.get("/health", summary="Health check")
async def health():
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
