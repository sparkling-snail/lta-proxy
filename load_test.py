"""
load_test.py — sends traffic to the LTA proxy to populate your Grafana dashboard.

Usage:
  # Normal traffic
  python load_test.py

  # Simulate a high-error incident (forces upstream errors by using bad stop codes)
  python load_test.py --chaos

  # Fast burst to test latency behaviour
  python load_test.py --burst
"""
import asyncio
import argparse
import random
import httpx
import time

BASE_URL = "http://localhost:8000"

# Real Sengkang-area bus stop codes to use as realistic load
BUS_STOPS = [
    "65199",  # Sengkang Int
    "65009",  # Compassvale Rd
    "65101",  # Rivervale Dr
    "65111",  # Sengkang West
    "65239",  # Fernvale Rd
]

# Bad codes to trigger upstream errors deliberately
BAD_STOPS = ["00000", "99999", "XXXXX"]


async def hit(client: httpx.AsyncClient, stop: str, label: str = ""):
    try:
        start = time.time()
        resp = await client.get(f"{BASE_URL}/arrivals/{stop}", timeout=6.0)
        elapsed = time.time() - start
        status = resp.status_code
        src = resp.headers.get("x-served-from", "live")
        print(f"[{label or stop}] HTTP {status} in {elapsed:.3f}s ({src})")
    except Exception as e:
        print(f"[{label or stop}] ERROR: {e}")


async def normal_traffic():
    """Steady ~2 req/s across real bus stops."""
    print("Running normal traffic (Ctrl+C to stop)...")
    async with httpx.AsyncClient() as client:
        while True:
            stop = random.choice(BUS_STOPS)
            await hit(client, stop)
            await asyncio.sleep(random.uniform(0.3, 0.8))


async def chaos_traffic():
    """Mix of real and bad stop codes to burn error budget — use for demo incidents."""
    print("Running CHAOS traffic — mixing good/bad stop codes (Ctrl+C to stop)...")
    async with httpx.AsyncClient() as client:
        while True:
            if random.random() < 0.4:   # 40% bad requests
                stop = random.choice(BAD_STOPS)
                await hit(client, stop, label="BAD")
            else:
                stop = random.choice(BUS_STOPS)
                await hit(client, stop)
            await asyncio.sleep(random.uniform(0.1, 0.4))


async def burst_traffic():
    """Fire 20 concurrent requests to spike latency metrics."""
    print("Running burst traffic (10 rounds)...")
    async with httpx.AsyncClient() as client:
        for i in range(10):
            tasks = [
                hit(client, random.choice(BUS_STOPS), label=f"burst-{j}")
                for j in range(20)
            ]
            await asyncio.gather(*tasks)
            print(f"--- burst {i+1}/10 done ---")
            await asyncio.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chaos", action="store_true", help="Inject errors")
    parser.add_argument("--burst", action="store_true", help="Burst latency test")
    args = parser.parse_args()

    try:
        if args.chaos:
            asyncio.run(chaos_traffic())
        elif args.burst:
            asyncio.run(burst_traffic())
        else:
            asyncio.run(normal_traffic())
    except KeyboardInterrupt:
        print("\nStopped.")
