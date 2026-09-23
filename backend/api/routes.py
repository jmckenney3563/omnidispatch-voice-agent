"""
REST API Routes for OmniDispatch Voice Agent.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from backend.config import get_settings
from backend.dispatch.mock_db import get_db
from backend.dispatch.models import FleetUnit, DispatchTicket, UnitStatus, Severity
from backend.dispatch.tools import TOOLS_SCHEMA, execute_tool
from backend.dispatch.engine import get_dispatch_engine
from backend.assemblyai.scenarios import get_all_scenarios, get_scenario_by_id

router = APIRouter(prefix="/api", tags=["OmniDispatch API"])


class CallInitiateRequest(BaseModel):
    scenario_id: Optional[str] = "scenario-1"
    caller_name: Optional[str] = "Anonymous Caller"
    caller_phone: Optional[str] = "911-CELL-GEO"
    live_mode: bool = False


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]


class TicketCreateRequest(BaseModel):
    incident_type: str
    severity: Severity = Severity.MEDIUM
    description: str
    address: str
    lat: float
    lng: float
    sector: str = "Metro-Central"
    assigned_units: List[str] = []


@router.get("/health")
async def health_check():
    settings = get_settings()
    has_api_key = bool(settings.assemblyai_api_key)
    return {
        "status": "ONLINE",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "assemblyai_status": "LIVE_API_READY" if has_api_key else "HIGH_FIDELITY_SIMULATION",
        "assemblyai_model": "Universal-3 Pro Realtime STT",
        "sample_rate_hz": settings.audio_sample_rate,
        "vad_silence_threshold_ms": settings.vad_silence_threshold_ms,
        "tools_loaded": len(TOOLS_SCHEMA)
    }


@router.get("/fleet", response_model=List[FleetUnit])
async def list_fleet():
    """Retrieves all active emergency and logistics units in fleet database."""
    database = get_db()
    return database.get_all_units()


@router.get("/fleet/{unit_id}", response_model=FleetUnit)
async def get_fleet_unit(unit_id: str):
    database = get_db()
    unit = database.get_unit(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail=f"Unit '{unit_id}' not found")
    return unit


@router.post("/fleet/reset")
async def reset_fleet():
    """Resets all fleet units and tickets to clean default simulation state."""
    database = get_db()
    database.reset_to_default()
    return {"status": "SUCCESS", "message": "Fleet database and tickets reset to defaults"}


@router.get("/tickets", response_model=List[DispatchTicket])
async def list_tickets():
    """Retrieves all emergency dispatch tickets."""
    database = get_db()
    return database.get_all_tickets()


@router.get("/tickets/{ticket_id}", response_model=DispatchTicket)
async def get_ticket(ticket_id: str):
    database = get_db()
    ticket = database.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")
    return ticket


@router.post("/tickets")
async def create_manual_ticket(req: TicketCreateRequest):
    """Manually creates a dispatch ticket (Operations Room Override)."""
    engine = get_dispatch_engine()
    res = await engine.execute_tool_for_session(
        session_id="manual-override",
        tool_name="assign_dispatch_ticket",
        arguments={
            "call_id": "manual-override",
            "incident_type": req.incident_type,
            "severity": req.severity.value,
            "location": {
                "address": req.address,
                "lat": req.lat,
                "lng": req.lng,
                "sector": req.sector
            },
            "assigned_unit_ids": req.assigned_units,
            "description": req.description
        }
    )
    return res["result"]


@router.get("/scenarios")
async def list_scenarios():
    """Retrieves the 3 high-stakes emergency dispatch scenarios."""
    return get_all_scenarios()


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    s = get_scenario_by_id(scenario_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return s


@router.get("/tools")
async def list_tools():
    """Returns the 6 standard tools in OpenAI / AssemblyAI JSON Schema format."""
    return {
        "count": len(TOOLS_SCHEMA),
        "tools": TOOLS_SCHEMA
    }


@router.post("/dispatch/tool-execute")
async def execute_tool_endpoint(req: ToolExecuteRequest):
    """Directly invokes any of the 6 tools for testing, benchmarking, or dispatcher overrides."""
    try:
        result = await execute_tool(req.tool_name, req.arguments)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dispatch/call")
async def initiate_call(req: CallInitiateRequest):
    """Initiates an emergency voice dispatch session."""
    engine = get_dispatch_engine()
    session = engine.create_session(caller_id=req.caller_phone)
    return {
        "status": "SESSION_INITIALIZED",
        "session_id": session.session_id,
        "caller_id": session.caller_id,
        "scenario_id": req.scenario_id,
        "live_mode": req.live_mode,
        "websocket_url": f"/ws/dispatch?session_id={session.session_id}&scenario_id={req.scenario_id or 'scenario-1'}"
    }
