"""
Tests for all 6 JSON-schema dispatch tools and dynamic executor.
"""
import pytest
from backend.dispatch.mock_db import get_db
from backend.dispatch.models import UnitStatus, Severity
from backend.dispatch.tools import (
    locate_caller_and_incident,
    lookup_fleet_units,
    calculate_incident_route,
    assess_incident_severity,
    assign_dispatch_ticket,
    send_driver_notification,
    execute_tool,
    TOOLS_SCHEMA
)


@pytest.fixture(autouse=True)
def reset_db_before_test():
    db = get_db()
    db.reset_to_default()
    yield
    db.reset_to_default()


def test_tools_schema_count_and_format():
    assert len(TOOLS_SCHEMA) == 6
    for item in TOOLS_SCHEMA:
        assert item["type"] == "function"
        fn = item["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert "properties" in fn["parameters"]


@pytest.mark.asyncio
async def test_locate_caller_and_incident_known():
    res = await locate_caller_and_incident("There is an accident on I-95 Mile 42")
    assert res["status"] == "LOCATED"
    assert "Interstate 95" in res["resolved_address"]
    assert res["sector"] == "Highway-North"
    assert res["lat"] > 0
    assert res["lng"] < 0


@pytest.mark.asyncio
async def test_locate_caller_and_incident_fallback():
    res = await locate_caller_and_incident("Unknown cabin in dense forest")
    assert res["status"] == "LOCATED"
    assert res["sector"] == "Metro-Central"


@pytest.mark.asyncio
async def test_lookup_fleet_units():
    # Lookup units near 40.75, -73.98
    res = await lookup_fleet_units(
        incident_lat=40.75,
        incident_lng=-73.98,
        unit_types=["EMS_AMBULANCE", "FIRE_ENGINE"],
        max_units=3
    )
    assert res["status"] == "SUCCESS"
    assert res["units_found_count"] > 0
    assert len(res["available_units"]) <= 3
    for u in res["available_units"]:
        assert u["status"] == "AVAILABLE"
        assert u["type"] in ["EMS_AMBULANCE", "FIRE_ENGINE"]
        assert u["distance_miles"] >= 0


@pytest.mark.asyncio
async def test_calculate_incident_route():
    res = await calculate_incident_route(
        unit_id="unit-101",
        incident_lat=40.7852,
        incident_lng=-73.9621,
        priority_mode="EMERGENCY_SIREN"
    )
    assert res["status"] == "ROUTE_CALCULATED"
    assert res["callsign"] == "Medic-101"
    assert res["distance_miles"] > 0
    assert res["eta_minutes"] > 0
    assert len(res["turn_by_turn"]) > 0


@pytest.mark.asyncio
async def test_assess_incident_severity():
    critical_res = await assess_incident_severity(
        incident_description="Chemical tanker leaking toxic yellow gas with trapped victim",
        hazards_reported=["toxic_chemical_spill", "trapped_personnel"],
        caller_stress_level="CRITICAL"
    )
    assert critical_res["severity"] == Severity.CRITICAL.value
    assert "HAZMAT_UNIT" in critical_res["recommended_unit_types"]

    high_res = await assess_incident_severity(
        incident_description="Freezing blizzard condition with biologics temperature warning"
    )
    assert high_res["severity"] == Severity.HIGH.value

    medium_res = await assess_incident_severity(
        incident_description="Minor fender bender on parking lot"
    )
    assert medium_res["severity"] == Severity.MEDIUM.value


@pytest.mark.asyncio
async def test_assign_dispatch_ticket():
    db = get_db()
    res = await assign_dispatch_ticket(
        call_id="call-test-99",
        incident_type="HAZMAT_SPILL",
        severity=Severity.CRITICAL.value,
        location={
            "address": "I-95 Northbound Mile 42",
            "lat": 40.7852,
            "lng": -73.9621,
            "sector": "Highway-North"
        },
        assigned_unit_ids=["unit-107", "unit-101"],
        description="Hazardous chemical spill requiring decontamination"
    )
    assert res["status"] == "DISPATCH_CONFIRMED"
    ticket_id = res["ticket_id"]
    assert ticket_id.startswith("TICK-")

    # Verify unit status updated to EN_ROUTE in db
    hazmat = db.get_unit("unit-107")
    assert hazmat is not None
    assert hazmat.status == UnitStatus.EN_ROUTE
    assert hazmat.assigned_ticket_id == ticket_id


@pytest.mark.asyncio
async def test_send_driver_notification():
    # First create ticket
    ticket_res = await assign_dispatch_ticket(
        call_id="call-test-100",
        incident_type="STRUCTURE_FIRE",
        severity=Severity.HIGH.value,
        location={
            "address": "820 Dock Street",
            "lat": 40.7135,
            "lng": -74.0125,
            "sector": "Industrial-Port"
        },
        assigned_unit_ids=["unit-104"],
        description="Warehouse fire"
    )
    ticket_id = ticket_res["ticket_id"]

    notif_res = await send_driver_notification(
        ticket_id=ticket_id,
        unit_id="unit-104",
        radio_instruction="Engine-4 respond to Dock Street warehouse fire Code 3.",
        urgency="IMMEDIATE_CODE_3"
    )
    assert notif_res["status"] == "TRANSMISSION_ACKNOWLEDGED"
    assert notif_res["callsign"] == "Engine-4"
    assert "MDT-" in notif_res["transmission_id"]


@pytest.mark.asyncio
async def test_execute_tool_dynamic():
    res = await execute_tool(
        "locate_caller_and_incident",
        {"raw_location_text": "Pier 44 dock warehouse"}
    )
    assert res["tool_name"] == "locate_caller_and_incident"
    assert "result" in res
    assert res["duration_ms"] >= 0

    with pytest.raises(ValueError):
        await execute_tool("non_existent_tool", {})
