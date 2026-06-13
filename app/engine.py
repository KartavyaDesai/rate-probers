import asyncio
import httpx
import time
from typing import Dict, Any
from .state import update_simulation_metrics, update_simulation_status

async def send_single_request(client: httpx.AsyncClient, target_url: str, method: str, headers: dict) -> int:
    """Fires a single HTTP request and returns the status code (or 0 for network failure)."""
    try:
        response = await client.request(method, target_url, headers=headers, timeout=5.0)
        return response.status_code
    except httpx.RequestError:
        return 0  # Represents a network drop or timeout

async def run_simulation_worker(sim_id: str, config: Dict[str, Any]):
    """
    The background loop. It chunks traffic into 1-second buckets
    to avoid crushing Python's event loop while simulating traffic shapes.
    """
    target_url = config["target_url"]
    method = config.get("method", "GET")
    headers = config.get("headers", {})
    duration = config["duration_seconds"]
    pattern = config["traffic_pattern"]
    base_rps = config["base_rps"]
    spike_rps = config.get("spike_rps", base_rps)
    spike_at_second = config.get("spike_at_second", 0)

    # Use a highly-configured client pool to prevent client-side bottlenecks
    limits = httpx.Limits(max_keepalive_connections=100, max_connections=500)
    
    async with httpx.AsyncClient(limits=limits) as client:
        for current_second in range(1, duration + 1):
            start_time = time.time()
            
            # Determine how many requests to send this specific second
            if pattern == "spike" and current_second == spike_at_second:
                current_rps = spike_rps
            else:
                current_rps = base_rps

            # Spawn all tasks concurrently for this 1-second batch
            tasks = [send_single_request(client, target_url, method, headers) for _ in range(current_rps)]
            status_codes = await asyncio.gather(*tasks)

            # Process results for this second
            accepted = sum(1 for code in status_codes if 200 <= code < 300)
            rate_limited = sum(1 for code in status_codes if code == 429)
            errors = sum(1 for code in status_codes if code == 0 or (code >= 400 and code != 429))

            # Push updates to our in-memory store immediately
            update_simulation_metrics(sim_id, accepted, rate_limited, errors)

            # Calculate how long the batch took, and sleep off the remainder of the second
            elapsed = time.time() - start_time
            sleep_time = max(0.0, 1.0 - elapsed)
            await asyncio.sleep(sleep_time)

        # Mark job as done
        update_simulation_status(sim_id, "completed")
