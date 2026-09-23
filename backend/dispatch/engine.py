"""
Dispatch State Machine & Autonomous Orchestrator for OmniDispatch.
Tracks session states, executes automated dispatch toolchain, and issues alerts.
"""
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from backend.dispatch.mock_db import get_db
from backend.dispatch.models import Severity, TicketStatus
from backend.dispatch.tools import execute_tool, TOOLS_SCHEMA


class DispatchSessionState:
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    EVALUATING_TOOLS = "EVALUATING_TOOLS"
    UNITS_DISPATCHED = "UNITS_DISPATCHED"
    RESOLVED = "RESOLVED"


class DispatchSession:
    def __init__(self, session_id: str, caller_id: Optional[str] = None):
        self.session_id = session_id
        self.caller_id = caller_id or f"CALLER-{uuid.uuid4().hex[:4].upper()}"
        self.state = DispatchSessionState.IDLE
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.transcript_history: List[Dict[str, Any]] = []
        self.tool_executions: List[Dict[str, Any]] = []
        self.location_data: Optional[Dict[str, Any]] = None
        self.severity_data: Optional[Dict[str, Any]] = None
        self.dispatched_ticket: Optional[Dict[str, Any]] = None
        self.assigned_units: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "caller_id": self.caller_id,
            "state": self.state,
            "created_at": self.created_at,
            "transcript_count": len(self.transcript_history),
            "tool_executions_count": len(self.tool_executions),
            "location_data": self.location_data,
            "severity_data": self.severity_data,
            "dispatched_ticket": self.dispatched_ticket,
            "assigned_units": self.assigned_units,
        }


class DispatchEngine:
    def __init__(self):
        self.sessions: Dict[str, DispatchSession] = {}
        self._listeners: List[Callable[[str, Dict[str, Any]], Any]] = []

    def subscribe(self, callback: Callable[[str, Dict[str, Any]], Any]):
        """Subscribes a listener (e.g. WebSocket manager) to dispatch events."""
        self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[str, Dict[str, Any]], Any]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def _emit(self, event_type: str, payload: Dict[str, Any]):
        for listener in self._listeners:
            try:
                res = listener(event_type, payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass

    def create_session(self, session_id: Optional[str] = None, caller_id: Optional[str] = None) -> DispatchSession:
        sid = session_id or str(uuid.uuid4())
        session = DispatchSession(sid, caller_id)
        session.state = DispatchSessionState.LISTENING
        self.sessions[sid] = session
        return session

    def get_session(self, session_id: str) -> Optional[DispatchSession]:
        return self.sessions.get(session_id)

    async def record_transcript(
        self,
        session_id: str,
        speaker: str,
        text: str,
        is_final: bool = True,
        confidence: float = 1.0,
        latency_ms: Optional[float] = None
    ):
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)

        turn_data = {
            "session_id": session_id,
            "speaker": speaker,
            "text": text,
            "is_final": is_final,
            "confidence": confidence,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if is_final:
            session.transcript_history.append(turn_data)

        await self._emit("transcript_update", turn_data)

    async def execute_tool_for_session(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Runs a tool, records execution event, and broadcasts state."""
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)

        session.state = DispatchSessionState.EVALUATING_TOOLS
        await self._emit("tool_start", {
            "session_id": session_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Execute tool
        execution = await execute_tool(tool_name, arguments)
        session.tool_executions.append(execution)

        # Update session memory based on tool outputs
        if tool_name == "locate_caller_and_incident":
            session.location_data = execution["result"]
        elif tool_name == "assess_incident_severity":
            session.severity_data = execution["result"]
        elif tool_name == "assign_dispatch_ticket":
            session.dispatched_ticket = execution["result"]
            session.assigned_units = arguments.get("assigned_unit_ids", [])
            session.state = DispatchSessionState.UNITS_DISPATCHED
            # Broadcast ticket created
            await self._emit("ticket_created", execution["result"])
            # Broadcast fleet status change
            database = get_db()
            await self._emit("fleet_updated", {
                "units": [u.model_dump() for u in database.get_all_units()]
            })

        await self._emit("tool_complete", {
            "session_id": session_id,
            "execution": execution
        })

        return execution

    async def run_autonomous_dispatch_pipeline(
        self,
        session_id: str,
        location_text: str,
        incident_description: str,
        required_unit_types: Optional[List[str]] = None,
        hazards: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Complete end-to-end automated 6-tool dispatch pipeline triggered autonomously
        upon caller turn completion:
        1. locate_caller_and_incident
        2. assess_incident_severity
        3. lookup_fleet_units
        4. calculate_incident_route
        5. assign_dispatch_ticket
        6. send_driver_notification (for each dispatched unit)
        """
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)

        # Step 1: Locate
        loc_res = await self.execute_tool_for_session(
            session_id,
            "locate_caller_and_incident",
            {"raw_location_text": location_text}
        )
        loc_data = loc_res["result"]

        # Step 2: Assess Severity
        sev_res = await self.execute_tool_for_session(
            session_id,
            "assess_incident_severity",
            {
                "incident_description": incident_description,
                "hazards_reported": hazards or [],
                "caller_stress_level": "CRITICAL" if "fire" in incident_description.lower() or "tanker" in incident_description.lower() else "ELEVATED"
            }
        )
        sev_data = sev_res["result"]

        # Step 3: Lookup Units
        req_types = required_unit_types or sev_data.get("recommended_unit_types", [])
        fleet_res = await self.execute_tool_for_session(
            session_id,
            "lookup_fleet_units",
            {
                "incident_lat": loc_data["lat"],
                "incident_lng": loc_data["lng"],
                "unit_types": req_types,
                "max_units": 3
            }
        )
        available_units = fleet_res["result"].get("available_units", [])
        if not available_units:
            # Fallback to any available units
            fallback_res = await self.execute_tool_for_session(
                session_id,
                "lookup_fleet_units",
                {
                    "incident_lat": loc_data["lat"],
                    "incident_lng": loc_data["lng"],
                    "max_units": 2
                }
            )
            available_units = fallback_res["result"].get("available_units", [])

        unit_ids_to_assign = [u["id"] for u in available_units[:2]]

        # Step 4: Calculate Route for Primary Unit
        route_data = None
        if unit_ids_to_assign:
            primary_id = unit_ids_to_assign[0]
            route_res = await self.execute_tool_for_session(
                session_id,
                "calculate_incident_route",
                {
                    "unit_id": primary_id,
                    "incident_lat": loc_data["lat"],
                    "incident_lng": loc_data["lng"],
                    "priority_mode": "EMERGENCY_SIREN"
                }
            )
            route_data = route_res["result"]

        # Step 5: Assign Dispatch Ticket
        incident_type = sev_data.get("incident_code", "EMERGENCY_GENERAL")
        ticket_res = await self.execute_tool_for_session(
            session_id,
            "assign_dispatch_ticket",
            {
                "call_id": session_id,
                "incident_type": incident_type,
                "severity": sev_data.get("severity", Severity.HIGH.value),
                "location": {
                    "address": loc_data["resolved_address"],
                    "lat": loc_data["lat"],
                    "lng": loc_data["lng"],
                    "sector": loc_data["sector"]
                },
                "assigned_unit_ids": unit_ids_to_assign,
                "description": incident_description
            }
        )
        ticket_data = ticket_res["result"]

        # Step 6: Send Driver Notifications to each assigned unit
        notifications = []
        for uid in unit_ids_to_assign:
            radio_msg = f"OmniDispatch Command to {uid}: Immediate Code-3 response ordered to {loc_data['resolved_address']}. Incident: {incident_description}."
            notif_res = await self.execute_tool_for_session(
                session_id,
                "send_driver_notification",
                {
                    "ticket_id": ticket_data["ticket_id"],
                    "unit_id": uid,
                    "radio_instruction": radio_msg,
                    "urgency": "IMMEDIATE_CODE_3"
                }
            )
            notifications.append(notif_res["result"])

        session.state = DispatchSessionState.UNITS_DISPATCHED

        return {
            "status": "PIPELINE_COMPLETE",
            "session_id": session_id,
            "ticket_id": ticket_data["ticket_id"],
            "assigned_units": unit_ids_to_assign,
            "route": route_data,
            "notifications_count": len(notifications),
            "total_tools_executed": len(session.tool_executions)
        }


# Global singleton engine
dispatch_engine = DispatchEngine()


def get_dispatch_engine() -> DispatchEngine:
    return dispatch_engine
