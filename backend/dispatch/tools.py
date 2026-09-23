"""
6 Standard JSON-Schema Dispatch Tools for OmniDispatch Voice Agent.
Compatible with AssemblyAI Voice Agent tool-calling / LLM tool-calling.
"""
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.dispatch.mock_db import get_db
from backend.dispatch.models import (
    UnitType,
    UnitStatus,
    Severity,
    TicketStatus,
    DispatchTicket,
    IncidentLocation,
)

# Known sectors and simulated geocoding reference points
GEOCACHE = [
    {
        "keywords": ["i-95", "interstate 95", "mile 42", "highway", "expressway", "mile marker"],
        "address": "Interstate 95 Northbound at Mile Marker 42, North Corridor Overpass",
        "lat": 40.7852,
        "lng": -73.9621,
        "sector": "Highway-North",
        "landmarks": ["Mile Marker 42", "Exit 8 Overpass", "North River Toll Plaza"],
        "risk_zone": "High-Speed Interstate / Hazmat Arterial",
    },
    {
        "keywords": ["warehouse", "dock", "industrial", "dock street", "pier", "harbor", "blaze", "fire"],
        "address": "Pier 44 Logistics Warehouse, 820 Dock Street",
        "lat": 40.7135,
        "lng": -74.0125,
        "sector": "Industrial-Port",
        "landmarks": ["Pier 44 Master Gate", "Dock Crane 2", "Hudson Maritime Bulkhead"],
        "risk_zone": "Industrial Heavy Storage / Flammable Hazard",
    },
    {
        "keywords": ["pharma", "cold chain", "vaccine", "blizzard", "route 9", "hudson pass", "refrigeration", "mountain"],
        "address": "Route 9 Alpine Pass, Mile Post 18 Mountain Cut",
        "lat": 40.8240,
        "lng": -73.9280,
        "sector": "Northern-Valley",
        "landmarks": ["Alpine Ridge Mile Post 18", "Northern Electric Substation", "Snow Clearing Turnout 3"],
        "risk_zone": "Severe Weather / Sub-Zero Mountain Pass",
    },
    {
        "keywords": ["broadway", "midtown", "times square", "42nd", "central", "times sq"],
        "address": "Broadway & West 48th Street, Metro Midtown",
        "lat": 40.7589,
        "lng": -73.9851,
        "sector": "Metro-Midtown",
        "landmarks": ["Times Square North", "Theater District Subway", "Duffy Square"],
        "risk_zone": "High Density Pedestrian / Urban Core",
    },
]

# Tool Definitions (OpenAI / AssemblyAI Compatible JSON Schema)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "locate_caller_and_incident",
            "description": "Geocodes or triangulates caller cellular/GPS data or spoken landmarks to exact coordinates, sector, and risk zone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "raw_location_text": {
                        "type": "string",
                        "description": "The verbatim location or landmark description spoken by the caller (e.g. 'I-95 Northbound Mile 42' or 'Pier 44 Warehouse')."
                    },
                    "caller_phone": {
                        "type": "string",
                        "description": "Caller phone or cellular triangulation ID."
                    },
                    "caller_name": {
                        "type": "string",
                        "description": "Caller name if identified."
                    }
                },
                "required": ["raw_location_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_fleet_units",
            "description": "Queries available emergency, fire, medical, hazmat, or cold-chain logistics units within radius of the incident coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_lat": {
                        "type": "number",
                        "description": "Latitude of the incident location."
                    },
                    "incident_lng": {
                        "type": "number",
                        "description": "Longitude of the incident location."
                    },
                    "unit_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of unit types (e.g. ['EMS_AMBULANCE', 'FIRE_ENGINE', 'HAZMAT_UNIT', 'HEAVY_RESCUE', 'COLD_CHAIN_REFRIGERATED', 'POLICE_PATROL'])."
                    },
                    "max_distance_miles": {
                        "type": "number",
                        "description": "Maximum search radius in miles (default 25)."
                    },
                    "max_units": {
                        "type": "integer",
                        "description": "Maximum number of units to return."
                    }
                },
                "required": ["incident_lat", "incident_lng"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_incident_route",
            "description": "Computes optimal emergency response route, mileage, traffic delay, and estimated time of arrival (ETA) for a specific fleet unit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "unit_id": {
                        "type": "string",
                        "description": "The unique ID of the fleet unit (e.g. 'unit-101')."
                    },
                    "incident_lat": {
                        "type": "number",
                        "description": "Target incident latitude."
                    },
                    "incident_lng": {
                        "type": "number",
                        "description": "Target incident longitude."
                    },
                    "priority_mode": {
                        "type": "string",
                        "enum": ["EMERGENCY_SIREN", "STANDARD_TRANSIT"],
                        "description": "Emergency siren priority clearance mode vs standard transit."
                    }
                },
                "required": ["unit_id", "incident_lat", "incident_lng"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assess_incident_severity",
            "description": "Analyzes incident description, physical hazards, trapped victims, and caller stress to classify severity (LOW, MEDIUM, HIGH, CRITICAL) and required protocols.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_description": {
                        "type": "string",
                        "description": "Detailed description of the incident from caller speech."
                    },
                    "hazards_reported": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of reported hazards, e.g. ['toxic_chemical_spill', 'structure_fire', 'trapped_personnel', 'hypothermia']."
                    },
                    "caller_stress_level": {
                        "type": "string",
                        "enum": ["LOW", "ELEVATED", "CRITICAL"],
                        "description": "Assessed emotional or acoustic stress level of caller."
                    }
                },
                "required": ["incident_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assign_dispatch_ticket",
            "description": "Creates an official Emergency Dispatch Ticket, assigns primary and secondary fleet units, updates unit statuses to EN_ROUTE, and saves to dispatch ledger.",
            "parameters": {
                "type": "object",
                "properties": {
                    "call_id": {
                        "type": "string",
                        "description": "The active voice call session ID."
                    },
                    "incident_type": {
                        "type": "string",
                        "description": "Short code or category (e.g. 'HAZMAT_HIGHWAY_COLLISION', 'WAREHOUSE_3ALARM_FIRE', 'COLDCHAIN_BREAKDOWN')."
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                        "description": "Assigned severity level."
                    },
                    "location": {
                        "type": "object",
                        "properties": {
                            "address": {"type": "string"},
                            "lat": {"type": "number"},
                            "lng": {"type": "number"},
                            "sector": {"type": "string"}
                        },
                        "required": ["address", "lat", "lng", "sector"],
                        "description": "Incident location coordinates and address."
                    },
                    "assigned_unit_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of fleet unit IDs to dispatch."
                    },
                    "description": {
                        "type": "string",
                        "description": "Summary notes for field units."
                    },
                    "caller_name": {
                        "type": "string",
                        "description": "Caller identification name."
                    }
                },
                "required": ["call_id", "incident_type", "severity", "location", "assigned_unit_ids", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_driver_notification",
            "description": "Transmits digital Mobile Data Terminal (MDT) alert and radio voice dispatch instructions to assigned unit drivers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The active dispatch ticket ID."
                    },
                    "unit_id": {
                        "type": "string",
                        "description": "Target fleet unit ID."
                    },
                    "radio_instruction": {
                        "type": "string",
                        "description": "Synthesized radio message broadcast to the crew."
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["ROUTINE", "URGENT", "IMMEDIATE_CODE_3"],
                        "description": "Broadcast urgency priority."
                    }
                },
                "required": ["ticket_id", "unit_id", "radio_instruction"]
            }
        }
    }
]


# Tool Implementations

async def locate_caller_and_incident(
    raw_location_text: str,
    caller_phone: Optional[str] = "911-CELL-GEO",
    caller_name: Optional[str] = "Anonymous"
) -> Dict[str, Any]:
    """Resolves caller location to precise geocoded coordinates and sector."""
    normalized = raw_location_text.lower()
    best_match = None
    for item in GEOCACHE:
        for kw in item["keywords"]:
            if kw in normalized:
                best_match = item
                break
        if best_match:
            break

    if not best_match:
        # Default to Metro-Midtown if unknown location
        best_match = {
            "address": raw_location_text,
            "lat": 40.7580,
            "lng": -73.9855,
            "sector": "Metro-Central",
            "landmarks": ["Central Sector GPS Triangulation Point"],
            "risk_zone": "General Urban Zone"
        }

    return {
        "status": "LOCATED",
        "resolved_address": best_match["address"],
        "lat": best_match["lat"],
        "lng": best_match["lng"],
        "sector": best_match["sector"],
        "landmarks": best_match.get("landmarks", []),
        "risk_zone": best_match.get("risk_zone", "Standard Response Zone"),
        "caller_info": {
            "name": caller_name or "Anonymous",
            "phone": caller_phone or "911-CELL-GEO",
            "triangulation_accuracy_meters": 12.5
        }
    }


async def lookup_fleet_units(
    incident_lat: float,
    incident_lng: float,
    unit_types: Optional[List[str]] = None,
    max_distance_miles: float = 25.0,
    max_units: int = 5
) -> Dict[str, Any]:
    """Finds closest available units based on coordinates and unit types."""
    database = get_db()
    type_filters = None
    if unit_types:
        type_filters = [UnitType(t) for t in unit_types if t in UnitType.__members__]

    all_matches = []
    # If specific unit types requested
    if type_filters:
        for t in type_filters:
            matches = database.find_units(
                unit_type=t,
                max_distance_miles=max_distance_miles,
                incident_lat=incident_lat,
                incident_lng=incident_lng,
                status=UnitStatus.AVAILABLE
            )
            all_matches.extend(matches)
    else:
        all_matches = database.find_units(
            max_distance_miles=max_distance_miles,
            incident_lat=incident_lat,
            incident_lng=incident_lng,
            status=UnitStatus.AVAILABLE
        )

    # Sort all by distance and take top max_units
    all_matches.sort(key=lambda x: x[1])
    selected = all_matches[:max_units]

    units_data = []
    for unit, dist in selected:
        eta = database.calculate_eta_minutes(dist)
        units_data.append({
            "id": unit.id,
            "callsign": unit.callsign,
            "type": unit.type.value,
            "status": unit.status.value,
            "distance_miles": dist,
            "eta_minutes": eta,
            "capabilities": unit.capabilities,
            "contact_freq": unit.contact_freq,
            "current_sector": unit.coordinates.sector,
            "crew_count": unit.crew_count
        })

    return {
        "status": "SUCCESS",
        "units_found_count": len(units_data),
        "incident_coordinates": {"lat": incident_lat, "lng": incident_lng},
        "available_units": units_data
    }


async def calculate_incident_route(
    unit_id: str,
    incident_lat: float,
    incident_lng: float,
    priority_mode: str = "EMERGENCY_SIREN"
) -> Dict[str, Any]:
    """Calculates route, ETA, corridor clearance for selected unit."""
    database = get_db()
    unit = database.get_unit(unit_id)
    if not unit:
        return {"status": "ERROR", "message": f"Unit with ID '{unit_id}' not found"}

    dist = database.calculate_distance_miles(
        unit.coordinates.lat,
        unit.coordinates.lng,
        incident_lat,
        incident_lng
    )

    # Emergency siren gets ~20% faster transit
    speed = 52.0 if priority_mode == "EMERGENCY_SIREN" else 38.0
    traffic_factor = 1.1 if priority_mode == "EMERGENCY_SIREN" else 1.35
    eta = database.calculate_eta_minutes(dist, speed_mph=speed, traffic_factor=traffic_factor)

    corridor = f"Primary Arterial Route via {unit.coordinates.sector} Express Highway"
    turn_steps = [
        f"Depart {unit.coordinates.address} heading toward Arterial Corridor",
        f"Enter expressway with Code-3 emergency siren priority override",
        f"Proceed {round(dist * 0.8, 1)} miles along direct response corridor",
        f"Exit towards {incident_lat:.4f}, {incident_lng:.4f} and establish staging perimeter"
    ]

    return {
        "status": "ROUTE_CALCULATED",
        "unit_id": unit.id,
        "callsign": unit.callsign,
        "distance_miles": round(dist, 2),
        "eta_minutes": eta,
        "priority_mode": priority_mode,
        "primary_corridor": corridor,
        "traffic_condition": "CLEAR_EMERGENCY_CORRIDOR" if priority_mode == "EMERGENCY_SIREN" else "MODERATE_URBAN",
        "turn_by_turn": turn_steps
    }


async def assess_incident_severity(
    incident_description: str,
    hazards_reported: Optional[List[str]] = None,
    caller_stress_level: str = "ELEVATED"
) -> Dict[str, Any]:
    """Evaluates hazards, transcript, and caller stress to classify response severity."""
    desc_lower = incident_description.lower()
    hazards = [h.lower() for h in (hazards_reported or [])]

    # Critical indicators
    is_critical = (
        "trapped" in desc_lower
        or "explosion" in desc_lower
        or "chemical" in desc_lower
        or "tanker" in desc_lower
        or "unconscious" in desc_lower
        or "collapse" in desc_lower
        or "trapped_personnel" in hazards
        or "toxic_chemical_spill" in hazards
        or caller_stress_level == "CRITICAL"
    )

    # High indicators
    is_high = (
        "fire" in desc_lower
        or "blaze" in desc_lower
        or "spill" in desc_lower
        or "blizzard" in desc_lower
        or "vaccine" in desc_lower
        or "cold chain" in desc_lower
        or "injury" in desc_lower
        or "structure_fire" in hazards
        or "hypothermia" in hazards
    )

    if is_critical:
        severity = Severity.CRITICAL
        urgency = "IMMEDIATE_LIFE_SAFETY"
        code = "CODE-1-CRITICAL-MULTIAGENCY"
        recommended = [
            UnitType.FIRE_ENGINE.value,
            UnitType.EMS_AMBULANCE.value,
            UnitType.HAZMAT_UNIT.value,
            UnitType.HEAVY_RESCUE.value
        ]
        protocols = [
            "Establish 500-meter safety standoff perimeter",
            "Dispatch Advanced Life Support (ALS) medical staging",
            "Activate Incident Command System (ICS-201)",
            "Notify Regional Hazmat & Environmental Safety Bureau"
        ]
    elif is_high:
        severity = Severity.HIGH
        urgency = "HIGH_PRIORITY_DISPATCH"
        code = "CODE-2-HIGH-PRIORITY"
        recommended = [
            UnitType.FIRE_ENGINE.value,
            UnitType.EMS_AMBULANCE.value,
            UnitType.COLD_CHAIN_REFRIGERATED.value
        ]
        protocols = [
            "Deploy nearest primary response unit with sirens",
            "Dispatch secondary backup unit for containment",
            "Alert regional receiving trauma / transfer center"
        ]
    else:
        severity = Severity.MEDIUM
        urgency = "STANDARD_EXPEDITED"
        code = "CODE-3-STANDARD"
        recommended = [UnitType.EMS_AMBULANCE.value, UnitType.POLICE_PATROL.value]
        protocols = [
            "Deploy single unit for preliminary scene assessment",
            "Maintain radio monitoring on dispatch frequency"
        ]

    return {
        "status": "ASSESSED",
        "severity": severity.value,
        "incident_code": code,
        "dispatch_urgency": urgency,
        "recommended_unit_types": recommended,
        "safety_protocols": protocols,
        "stress_analysis": {
            "caller_stress": caller_stress_level,
            "hazards_count": len(hazards),
            "threat_multiplier": 1.5 if is_critical else (1.2 if is_high else 1.0)
        }
    }


async def assign_dispatch_ticket(
    call_id: str,
    incident_type: str,
    severity: str,
    location: Dict[str, Any],
    assigned_unit_ids: List[str],
    description: str,
    caller_name: Optional[str] = "Anonymous"
) -> Dict[str, Any]:
    """Creates immutable dispatch ticket and transitions assigned units to EN_ROUTE."""
    database = get_db()
    ticket_num = str(uuid.uuid4())[:8].upper()
    ticket_id = f"TICK-{ticket_num}"
    now_iso = datetime.now(timezone.utc).isoformat()

    loc_obj = IncidentLocation(
        address=location.get("address", "Sector Coordinates"),
        lat=float(location.get("lat", 40.7580)),
        lng=float(location.get("lng", -73.9855)),
        sector=location.get("sector", "Metro-Central"),
        landmarks=location.get("landmarks", []),
        risk_zone=location.get("risk_zone", "Standard")
    )

    sev_enum = Severity(severity) if severity in Severity.__members__ else Severity.MEDIUM

    ticket = DispatchTicket(
        id=ticket_id,
        call_id=call_id,
        timestamp=now_iso,
        caller_name=caller_name or "Anonymous",
        caller_phone="911-CELL-GEO",
        incident_type=incident_type,
        severity=sev_enum,
        location=loc_obj,
        description=description,
        assigned_units=assigned_unit_ids,
        status=TicketStatus.DISPATCHED,
        audit_log=[
            {
                "timestamp": now_iso,
                "action": "TICKET_CREATED_AND_DISPATCHED",
                "units": assigned_unit_ids,
                "author": "OmniDispatch Autonomous Voice Agent"
            }
        ]
    )

    # Save to mock database
    database.save_ticket(ticket)

    # Update assigned fleet units status to EN_ROUTE
    dispatched_info = []
    for uid in assigned_unit_ids:
        unit = database.get_unit(uid)
        if unit:
            dist = database.calculate_distance_miles(
                unit.coordinates.lat,
                unit.coordinates.lng,
                loc_obj.lat,
                loc_obj.lng
            )
            eta = database.calculate_eta_minutes(dist)
            database.update_unit_status(
                unit_id=uid,
                status=UnitStatus.EN_ROUTE,
                ticket_id=ticket_id,
                eta_minutes=eta
            )
            dispatched_info.append({
                "id": unit.id,
                "callsign": unit.callsign,
                "type": unit.type.value,
                "status": UnitStatus.EN_ROUTE.value,
                "eta_minutes": eta,
                "contact_freq": unit.contact_freq
            })

    return {
        "status": "DISPATCH_CONFIRMED",
        "ticket_id": ticket_id,
        "call_id": call_id,
        "incident_type": incident_type,
        "severity": sev_enum.value,
        "timestamp": now_iso,
        "dispatched_units": dispatched_info,
        "incident_address": loc_obj.address
    }


async def send_driver_notification(
    ticket_id: str,
    unit_id: str,
    radio_instruction: str,
    urgency: str = "IMMEDIATE_CODE_3"
) -> Dict[str, Any]:
    """Transmits Mobile Data Terminal alert and radio dispatch audio/text to assigned vehicle."""
    database = get_db()
    unit = database.get_unit(unit_id)
    if not unit:
        return {"status": "ERROR", "message": f"Unit '{unit_id}' not found"}

    ticket = database.get_ticket(ticket_id)
    dest_address = ticket.location.address if ticket else "Designated Target Sector"
    dest_coords = {"lat": ticket.location.lat, "lng": ticket.location.lng} if ticket else {
        "lat": unit.coordinates.lat, "lng": unit.coordinates.lng
    }

    transmission_id = f"MDT-{uuid.uuid4().hex[:6].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    mdt_packet = {
        "transmission_id": transmission_id,
        "ticket_id": ticket_id,
        "target_unit": unit.callsign,
        "unit_id": unit.id,
        "frequency": unit.contact_freq,
        "urgency": urgency,
        "destination": dest_address,
        "coordinates": dest_coords,
        "voice_synthesis_transcript": radio_instruction,
        "acknowledged": True,
        "ack_timestamp": now_iso
    }

    if ticket:
        ticket.audit_log.append({
            "timestamp": now_iso,
            "action": f"DRIVER_NOTIFICATION_TRANSMITTED to {unit.callsign}",
            "transmission_id": transmission_id
        })

    return {
        "status": "TRANSMISSION_ACKNOWLEDGED",
        "transmission_id": transmission_id,
        "unit_id": unit.id,
        "callsign": unit.callsign,
        "contact_freq": unit.contact_freq,
        "urgency": urgency,
        "mdt_payload": mdt_packet,
        "sent_at": now_iso
    }


# Map of tool names to functions for dynamic dispatch
TOOL_REGISTRY = {
    "locate_caller_and_incident": locate_caller_and_incident,
    "lookup_fleet_units": lookup_fleet_units,
    "calculate_incident_route": calculate_incident_route,
    "assess_incident_severity": assess_incident_severity,
    "assign_dispatch_ticket": assign_dispatch_ticket,
    "send_driver_notification": send_driver_notification,
}


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a dispatch tool by name with arguments and timing benchmarks."""
    start_time = time.perf_counter()
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown dispatch tool: '{tool_name}'")

    func = TOOL_REGISTRY[tool_name]
    result = await func(**arguments)
    duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
