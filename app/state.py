import uuid
from typing import Dict, Any
from pydantic import BaseModel

# In-memory database replacement
SIMULATION_STORE: Dict[str, Dict[str, Any]] = {}

def create_simulation_entry() -> str:
    """Initializes a simulation in memory and returns its unique ID."""
    sim_id = f"sim_{uuid.uuid4().hex[:8]}"
    SIMULATION_STORE[sim_id] = {
        "status": "running",
        "metrics": {
            "total_sent": 0,
            "accepted_requests": 0,
            "rate_limited_requests": 0,
            "other_errors": 0,
            "success_rate_percentage": 0.0
        }
    }
    return sim_id

def update_simulation_metrics(sim_id: str, accepted: int, rate_limited: int, errors: int):
    """Increments metrics dynamically as the simulation runs."""
    if sim_id in SIMULATION_STORE:
        store = SIMULATION_STORE[sim_id]["metrics"]
        store["accepted_requests"] += accepted
        store["rate_limited_requests"] += rate_limited
        store["other_errors"] += errors
        store["total_sent"] = store["accepted_requests"] + store["rate_limited_requests"] + store["other_errors"]
        
        # Calculate success rate safely
        if store["total_sent"] > 0:
            store["success_rate_percentage"] = round((store["accepted_requests"] / store["total_sent"]) * 100, 2)

def update_simulation_status(sim_id: str, status: str):
    """Updates the status (running, completed, failed)."""
    if sim_id in SIMULATION_STORE:
        SIMULATION_STORE[sim_id]["status"] = status
