"""
Tests for FastAPI REST endpoints and WebSocket connection handling.
"""
import pytest
from starlette.testclient import TestClient
from backend.main import app
from backend.dispatch.mock_db import get_db


@pytest.fixture(autouse=True)
def reset_db_before_test():
    db = get_db()
    db.reset_to_default()
    yield
    db.reset_to_default()


@pytest.fixture
def client():
    return TestClient(app)


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "Universal-3 Pro" in data["assemblyai_model"]
    assert data["tools_loaded"] == 6


def test_api_fleet_endpoints(client):
    # List fleet
    res = client.get("/api/fleet")
    assert res.status_code == 200
    units = res.json()
    assert len(units) >= 9

    # Single unit
    unit_res = client.get("/api/fleet/unit-101")
    assert unit_res.status_code == 200
    assert unit_res.json()["callsign"] == "Medic-101"

    # Non-existent unit
    missing_res = client.get("/api/fleet/non-existent-unit")
    assert missing_res.status_code == 404


def test_api_fleet_reset(client):
    res = client.post("/api/fleet/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"


def test_api_scenarios_endpoints(client):
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 3

    s1_res = client.get("/api/scenarios/scenario-1")
    assert s1_res.status_code == 200
    assert s1_res.json()["id"] == "scenario-1"

    not_found = client.get("/api/scenarios/unknown-scenario")
    assert not_found.status_code == 404


def test_api_tools_endpoint(client):
    res = client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 6
    names = [t["function"]["name"] for t in data["tools"]]
    assert "locate_caller_and_incident" in names
    assert "lookup_fleet_units" in names
    assert "calculate_incident_route" in names
    assert "assess_incident_severity" in names
    assert "assign_dispatch_ticket" in names
    assert "send_driver_notification" in names


def test_api_tool_execute_endpoint(client):
    payload = {
        "tool_name": "locate_caller_and_incident",
        "arguments": {"raw_location_text": "I-95 Northbound Mile 42"}
    }
    res = client.post("/api/dispatch/tool-execute", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["tool_name"] == "locate_caller_and_incident"
    assert data["result"]["status"] == "LOCATED"


def test_api_create_manual_ticket_and_list(client):
    ticket_payload = {
        "incident_type": "HIGHWAY_HAZARD",
        "severity": "HIGH",
        "description": "Debris scattered across Highway 95",
        "address": "I-95 Mile 42",
        "lat": 40.7852,
        "lng": -73.9621,
        "sector": "Highway-North",
        "assigned_units": ["unit-204"]
    }
    create_res = client.post("/api/tickets", json=ticket_payload)
    assert create_res.status_code == 200
    created = create_res.json()
    ticket_id = created["ticket_id"]

    # Verify listing tickets includes this ticket
    list_res = client.get("/api/tickets")
    assert list_res.status_code == 200
    tickets = list_res.json()
    assert any(t["id"] == ticket_id for t in tickets)

    # Get single ticket
    single_res = client.get(f"/api/tickets/{ticket_id}")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == ticket_id


def test_api_dispatch_call_initiate(client):
    res = client.post("/api/dispatch/call", json={"scenario_id": "scenario-2"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SESSION_INITIALIZED"
    assert "session_id" in data
    assert "websocket_url" in data


def test_websocket_connection_and_ping(client):
    with client.websocket_connect("/ws/dispatch?scenario_id=none") as websocket:
        # Initial greeting notification
        data = websocket.receive_json()
        assert data["event"] == "system_notification"

        # Send ping
        websocket.send_json({"action": "ping"})
        response = websocket.receive_json()
        assert response["event"] == "pong"
