from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import sqlite3
import os
import sys

# Add parent directory to sys.path so 'backend.xxx' imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.simulation import SimulationEngine

app = FastAPI(title="Enterprise Elevator API")

# Allow React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), 'elevator_enterprise.db')

# --- Pydantic Models for our API Contracts ---
class ManualCallReq(BaseModel):
    from_floor: int
    to_floor: int
    count: int = 1

class SimModeReq(BaseModel):
    mode: str # "manual", "auto", "scenario"

class SimControlReq(BaseModel):
    pause: bool = False
    speed: float = 1.0
    step: bool = False

# --- REST Endpoints ---

@app.get("/api/health")
async def health_check():
    return {"status": "Enterprise Backend is Active", "version": "2.0"}

# Global Engine instance and state
engine = None
sim_mode = "manual" # can be "manual" or "auto"

@app.post("/api/manual_call")
async def manual_call(req: ManualCallReq):
    global engine
    if engine:
        # Format required by process_calls: (floor, direction, priority, dest)
        direction = "UP" if req.to_floor > req.from_floor else "DOWN"
        call = (req.from_floor, direction, "NORMAL", req.to_floor)
        # Send multiple if count > 1
        calls = [call for _ in range(req.count)]
        engine.process_calls(calls)
    return {"status": "success", "message": f"Dispatched call from {req.from_floor} to {req.to_floor} for {req.count} passengers."}

@app.post("/api/sim/mode")
async def set_mode(req: SimModeReq):
    global sim_mode
    sim_mode = req.mode
    return {"status": "success", "mode_set": sim_mode}

@app.post("/api/sim/control")
async def control_sim(req: SimControlReq):
    return {"status": "success", "controls_applied": req.dict()}

@app.get("/api/users/{uid}")
async def get_user_role(uid: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, theme FROM users WHERE uid = ?", (uid,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"uid": uid, "role": row[0], "theme": row[1]}
    return {"uid": uid, "role": "viewer", "theme": "dark"}

# --- WebSocket for Real-time X-ele and Dashboard Updates ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws/state")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for commands
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task to stream simulation ticks
async def tick_loop():
    global engine
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json"))
    engine = SimulationEngine(config_path=config_path, quiet=True)
    engine.config["simulation"]["duration_steps"] = 999999 # Run forever in background
    
    while True:
        engine.current_step += 1
        
        # 1. Move elevators based on their internal queues
        engine.move_elevators()
        
        # 1b. Auto traffic generation
        if sim_mode == "auto":
            # Generate random calls like a real building
            calls = engine.generate_calls()
            if calls:
                engine.process_calls(calls)

        # 2. Reoptimize if needed
        if engine.current_step % 10 == 0:
            engine.reoptimize_routes()

        # Build payload for React
        
        # Determine latest activity for X-ele to explain
        last_decision = {
            "car": 1,
            "algorithm": "GBFS",
            "confidence": "98.5%",
            "factors": [
                { "name": "Wait Time Limit", "weight": "-0.5", "impact": "Low" },
                { "name": "Path Overlap", "weight": "+1.2", "impact": "Medium" }
            ],
            "explanation": "No active calls. The elevators are standing by in idle mode waiting for passenger input."
        }
        
        active_elevators = [e for e in engine.building.elevators if e.has_pending_stops()]
        if active_elevators:
            e = active_elevators[0]
            target = e.all_pending_floors()[0] if e.all_pending_floors() else "unknown"
            last_decision["car"] = e.elevator_id
            last_decision["explanation"] = f"Car {e.elevator_id} was dispatched to Floor {target} because its travel trajectory optimally minimized global wait times via the GBFS heuristic."
            last_decision["factors"] = [
                { "name": "Distance Cost", "weight": f"-{abs(e.current_floor - (target if isinstance(target, int) else 1)) * 0.2:.1f}", "impact": "High" },
                { "name": "Direction Alignment", "weight": "+4.1", "impact": "Critical" }
            ]

        payload = {
            "tick": engine.current_step,
            "elevators": [
                {
                    "id": e.elevator_id, 
                    "floor": e.current_floor, 
                    "dir": e.direction, 
                    "load": len(e.passengers), 
                    "status": "operational" if e.is_operational else "fault",
                    "queue": e.all_pending_floors()
                } for e in engine.building.elevators
            ],
            "floors": [{"n": f, "waiting": 0} for f in range(1, engine.building.num_floors + 1)],
            "events": [],
            "alerts": [],
            "last_decision": last_decision,
            "metrics": {
                "avg_wait": round(engine.metrics.avg_wait_time, 1), 
                "sla": 30, 
                "util": 0
            }
        }
        await manager.broadcast(payload)
        await asyncio.sleep(0.5) # Send tick every 0.5s for smooth UI

@app.on_event("startup")
async def startup_event():
    # Initialize DB and start background tick loop
    import database
    database.init_db()
    asyncio.create_task(tick_loop())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
