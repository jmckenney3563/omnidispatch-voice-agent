"""
In-memory Mock Database for Fleet Units, Dispatch Tickets, and Geospatial calculations.
"""
import math
import copy
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timezone
from backend.dispatch.models import (
    FleetUnit,
    UnitType,
    UnitStatus,
    Coordinates,
    DispatchTicket,
    IncidentLocation,
    Severity,
    TicketStatus,
)

DEFAULT_FLEET: List[Dict] = [
    {
        "id": "unit-101",
        "callsign": "Medic-101",
        "type": UnitType.EMS_AMBULANCE,
        "status": UnitStatus.AVAILABLE,
        "coordinates": {"lat": 40.7580, "lng": -73.9855, "sector": "Metro-North", "address": "Station 12, Broadway & 48th"},
        "speed_mph": 0.0,
        "capabilities": ["ALS (Advanced Life Support)", "Trauma", "Defibrillator", "Lucas Chest Compression"],
        "contact_freq": "155.340 MHz (EMS-1)",
        "crew_count": 2,
    },
    {
        "id": "unit-104",
        "callsign": "Engine-4",
        "type": UnitType.FIRE_ENGINE,
        "status": UnitStatus.AVAILABLE,
        "coordinates": {"lat": 40.7520, "lng": -73.9770, "sector": "Metro-Midtown", "address": "Engine Co 4, 3rd Ave"},
        "speed_mph": 0.0,
        "capabilities": ["1500 GPM Water Pumper", "Class-A & B Foam", "Thermal Imaging", "Hydrant Master"],
        "contact_freq": "154.280 MHz (FIRE-TAC1)",
        "crew_count": 4,
    },
    {
        "id": "unit-112",
        "callsign": "Ladder-12",
        "type": UnitType.AERIAL_LADDER,
        "status": UnitStatus.AVAILABLE,
        "coordinates": {"lat": 40.7600, "lng": -73.9950, "sector": "Metro-West", "address": "Ladder Co 12, 10th Ave"},
        "speed_mph": 0.0,
        "capabilities": ["100ft Aerial Platform", "Roof Ventilation", "High-Angle Rope Rescue"],
        "contact_freq": "154.280 MHz (FIRE-TAC1)",
        "crew_count": 4,
    },
    {
        "id": "unit-107",
        "callsign": "Hazmat-7",
        "type": UnitType.HAZMAT_UNIT,
        "status": UnitStatus.AVAILABLE,
        "coordinates": {"lat": 40.7120, "lng": -74.0150, "sector": "Industrial-Port", "address": "Hazmat HQ, Battery Park Pier"},
        "speed_mph": 0.0,
        "capabilities": ["Level-A Chemical Vapor Suits", "Atmospheric Sensing", "Mass Decon Showers", "Neutralizing Agents"],
        "contact_freq": "154.385 MHz (HAZMAT-OPS)",
        "crew_count": 3,
    },
    {
        "id": "unit-103",
        "callsign": "Rescue-3",
        "type": UnitType.HEAVY_RESCUE,
        "status": UnitStatus.AVAILABLE,
        "coordinates": {"lat": 40.7300, "lng": -73.9900, "sector": "South-Corridor", "address": "Rescue 3 Station, Union Sq"},
        "speed_mph": 0.0,
        "capabilities": ["Hydraulic Jaws of Life", "Trench Shoring", "Structural Collapse Rigging", "Heavy Winches"],
        "contact_freq": "154.310 MHz (RESCUE-CMD)",
        "crew_count": 4,
    },
    {
        "id": "unit-188",
        "callsign": "Logistics-88",
        "type": UnitType.LOGISTICS_SUPPORT,
        "status": UnitStatus.AVAILABLE,
        "coordinates": {"lat": 40.7700, "lng": -73.8700, "sector": "Transit-Hub", "address": "Logistics Depot, LaGuardia Perimeter"},
        "speed_mph": 0.0,
        "capabilities": ["Mobile 250kW Generator", "Emergency Fuel Transfer", "Lighting Towers", "Water Distribution"],
        "contact_freq": "460.500 MHz (LOG-TAC)",
        "crew_count": 2,
    },
    {
        "id": "unit-109",
        "callsign": "ColdChain-09",
        "type": UnitType.COLD_CHAIN_REFRIGERATED,
        "status": UnitStatus.AVAILABLE,
        "coordinates": {"lat": 40.8200, "lng": -73.9300, "sector": "Northern-Valley", "address": "BioPharma Logistics Base, Bronx South"},
        "speed_mph": 0.0,
        "capabilities": ["-80C Deep Freeze Chamber", "Dual Cryogenic Backup", "Live Telemetry Vaccine Vault"],
        "contact_freq": "461.125 MHz (COLD-DISP)",
        "crew_count": 2,
    },
    {
        "id": "unit-204",
        "callsign": "Patrol-204",
        "type": UnitType.POLICE_PATROL,
        "status": UnitStatus.AVAILABLE,
        "coordinates": {"lat": 40.7850, "lng": -73.9600, "sector": "Highway-North", "address": "Highway Patrol Post 4, I-95 Connector"},
        "speed_mph": 0.0,
        "capabilities": ["Highway Perimeter Lockdown", "High-Speed Interceptor", "Spike Strips", "Emergency Escort"],
        "contact_freq": "470.850 MHz (HWY-PATROL)",
        "crew_count": 2,
    },
    {
        "id": "unit-108",
        "callsign": "Medic-108",
        "type": UnitType.EMS_AMBULANCE,
        "status": UnitStatus.AVAILABLE,
        "coordinates": {"lat": 40.7450, "lng": -73.9650, "sector": "Metro-East", "address": "EMS Station 7, Queensboro South"},
        "speed_mph": 0.0,
        "capabilities": ["BLS (Basic Life Support)", "AED", "Oxygen Delivery", "Wheelchair / Stretcher Transport"],
        "contact_freq": "155.340 MHz (EMS-1)",
        "crew_count": 2,
    }
]


class FleetDatabase:
    def __init__(self):
        self._units: Dict[str, FleetUnit] = {}
        self._tickets: Dict[str, DispatchTicket] = {}
        self.reset_to_default()

    def reset_to_default(self):
        """Resets the fleet and tickets back to initial default state."""
        self._units.clear()
        self._tickets.clear()
        for u in DEFAULT_FLEET:
            data = copy.deepcopy(u)
            self._units[data["id"]] = FleetUnit(**data)

    def get_all_units(self) -> List[FleetUnit]:
        return list(self._units.values())

    def get_unit(self, unit_id: str) -> Optional[FleetUnit]:
        return self._units.get(unit_id)

    def update_unit_status(
        self,
        unit_id: str,
        status: UnitStatus,
        ticket_id: Optional[str] = None,
        eta_minutes: Optional[float] = None
    ) -> Optional[FleetUnit]:
        unit = self._units.get(unit_id)
        if not unit:
            return None
        unit.status = status
        if ticket_id is not None:
            unit.assigned_ticket_id = ticket_id
        if eta_minutes is not None:
            unit.eta_minutes = eta_minutes
        elif status == UnitStatus.AVAILABLE:
            unit.eta_minutes = None
            unit.assigned_ticket_id = None
        return unit

    def find_units(
        self,
        unit_type: Optional[UnitType] = None,
        max_distance_miles: Optional[float] = None,
        incident_lat: Optional[float] = None,
        incident_lng: Optional[float] = None,
        status: Optional[UnitStatus] = UnitStatus.AVAILABLE
    ) -> List[Tuple[FleetUnit, float]]:
        """
        Finds units matching criteria, sorted by distance from incident.
        Returns list of tuples: (FleetUnit, distance_in_miles)
        """
        results = []
        for unit in self._units.values():
            if status is not None and unit.status != status:
                continue
            if unit_type is not None and unit.type != unit_type:
                continue

            dist = 0.0
            if incident_lat is not None and incident_lng is not None:
                dist = self.calculate_distance_miles(
                    unit.coordinates.lat,
                    unit.coordinates.lng,
                    incident_lat,
                    incident_lng
                )
                if max_distance_miles is not None and dist > max_distance_miles:
                    continue

            results.append((unit, round(dist, 2)))

        # Sort by distance
        results.sort(key=lambda x: x[1])
        return results

    @staticmethod
    def calculate_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine formula to compute great-circle distance between two GPS points in miles."""
        earth_radius_miles = 3958.8
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return earth_radius_miles * c

    @staticmethod
    def calculate_eta_minutes(distance_miles: float, speed_mph: float = 40.0, traffic_factor: float = 1.25) -> float:
        """Calculates estimated response time in minutes considering traffic delay."""
        if speed_mph <= 0:
            speed_mph = 35.0
        time_hours = (distance_miles / speed_mph) * traffic_factor
        minutes = max(1.0, time_hours * 60.0)
        return round(minutes, 1)

    def save_ticket(self, ticket: DispatchTicket) -> DispatchTicket:
        self._tickets[ticket.id] = ticket
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[DispatchTicket]:
        return self._tickets.get(ticket_id)

    def get_all_tickets(self) -> List[DispatchTicket]:
        return list(self._tickets.values())

    def update_ticket_status(
        self,
        ticket_id: str,
        status: TicketStatus,
        note: Optional[str] = None
    ) -> Optional[DispatchTicket]:
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None
        ticket.status = status
        now_str = datetime.now(timezone.utc).isoformat()
        ticket.audit_log.append({
            "timestamp": now_str,
            "action": f"Status changed to {status.value}",
            "note": note or "Status update"
        })
        return ticket


# Global singleton instance
db = FleetDatabase()


def get_db() -> FleetDatabase:
    return db
