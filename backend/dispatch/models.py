"""
Pydantic data models for OmniDispatch domain entities.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class UnitType(str, Enum):
    EMS_AMBULANCE = "EMS_AMBULANCE"
    FIRE_ENGINE = "FIRE_ENGINE"
    AERIAL_LADDER = "AERIAL_LADDER"
    HAZMAT_UNIT = "HAZMAT_UNIT"
    HEAVY_RESCUE = "HEAVY_RESCUE"
    LOGISTICS_SUPPORT = "LOGISTICS_SUPPORT"
    COLD_CHAIN_REFRIGERATED = "COLD_CHAIN_REFRIGERATED"
    POLICE_PATROL = "POLICE_PATROL"


class UnitStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    RETURNING = "RETURNING"
    OFFLINE = "OFFLINE"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    DISPATCHED = "DISPATCHED"
    ON_SCENE = "ON_SCENE"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class Coordinates(BaseModel):
    lat: float
    lng: float
    sector: str = "Metro-Central"
    address: Optional[str] = None


class FleetUnit(BaseModel):
    id: str
    callsign: str
    type: UnitType
    status: UnitStatus = UnitStatus.AVAILABLE
    coordinates: Coordinates
    speed_mph: float = 0.0
    capabilities: List[str] = Field(default_factory=list)
    eta_minutes: Optional[float] = None
    assigned_ticket_id: Optional[str] = None
    contact_freq: str = "154.280 MHz"
    crew_count: int = 2


class IncidentLocation(BaseModel):
    address: str
    lat: float
    lng: float
    sector: str
    landmarks: List[str] = Field(default_factory=list)
    risk_zone: str = "Standard"


class DispatchTicket(BaseModel):
    id: str
    call_id: str
    timestamp: str
    caller_name: Optional[str] = "Anonymous"
    caller_phone: Optional[str] = "911-CELL-GEO"
    incident_type: str
    severity: Severity = Severity.MEDIUM
    location: IncidentLocation
    description: str
    assigned_units: List[str] = Field(default_factory=list)
    route_info: Optional[Dict[str, Any]] = None
    status: TicketStatus = TicketStatus.OPEN
    audit_log: List[Dict[str, Any]] = Field(default_factory=list)


class AudioPacket(BaseModel):
    sample_rate: int = 16000
    data_base64: str
    is_final: bool = False
    timestamp: float
    energy_level: float = 0.0


class ToolCallEvent(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    execution_time_ms: float
    timestamp: str


class VoiceTurn(BaseModel):
    speaker: str  # "caller" | "agent" | "system"
    text: str
    confidence: float = 1.0
    timestamp: str
    is_final: bool = True
    latency_ms: Optional[float] = None
