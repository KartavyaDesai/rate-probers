from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict
from .state import SIMULATION_STORE, create_simulation_entry
from .engine import run_simulation_worker

app = FastAPI(title="API Rate Limit Prober")

class SimulationRequest(BaseModel):
    target_url: str  # Kept as string for basic parsing ease, or use HttpUrl
    method: str = "GET"
    headers: Optional[Dict[str, str]] = {}
    duration_seconds: int = Field(..., gt=0, le=60) # Max 60 seconds to protect memory
    traffic_pattern: str  # "constant" or "spike"
    base_rps: int = Field(..., gt=0, le=200)
    spike_rps: Optional[int] = 0
    spike_at_second: Optional[int] = 0

@app.post("/api/v1/simulations", status_code=status.HTTP_202_ACCEPTED)
async def start_simulation(payload: SimulationRequest, background_tasks: BackgroundTasks):
    # 1. Create entry in our global dictionary
    sim_id = create_simulation_entry()
    
    # 2. Hand over execution to the async background worker
    background_tasks.add_task(run_simulation_worker, sim_id, payload.model_dump())
    
    # 3. Hand back the receipt instantly
    return {"simulation_id": sim_id, "status": "running"}

@app.get("/api/v1/simulations/{simulation_id}")
async def get_simulation_results(simulation_id: str):
    # Look directly into our global state object
    if simulation_id not in SIMULATION_STORE:
        raise HTTPException(status_code=404, detail="Simulation profile not found")
        
    return SIMULATION_STORE[simulation_id]
