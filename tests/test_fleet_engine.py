"""
Tests for Fleet Database, Distance Calculations, and Dispatch Engine Pipeline.
"""
import pytest
from backend.dispatch.mock_db import get_db, FleetDatabase
from backend.dispatch.models import UnitStatus, TicketStatus
from backend.dispatch.engine import get_dispatch_engine, DispatchSessionState


@pytest.fixture(autouse=True)
def reset_db_before_test():
    db = get_db()
    db.reset_to_default()
    yield
    db.reset_to_default()


def test_fleet_database_initialization():
    db = get_db()
    units = db.get_all_units()
    assert len(units) >= 9
    for u in units:
        assert u.status == UnitStatus.AVAILABLE
        assert u.coordinates.lat != 0
        assert u.coordinates.lng != 0


def test_haversine_distance_calculation():
    # Distance between NYC Times Square (40.7580, -73.9855) and Wall St (40.7075, -74.0090) ~ 3.6 miles
    dist = FleetDatabase.calculate_distance_miles(40.7580, -73.9855, 40.7075, -74.0090)
    assert 3.0 < dist < 4.5


def test_eta_calculation():
    eta = FleetDatabase.calculate_eta_minutes(distance_miles=5.0, speed_mph=40.0, traffic_factor=1.2)
    # (5 / 40) * 1.2 * 60 = 9.0 minutes
    assert abs(eta - 9.0) < 0.2


def test_dispatch_engine_session_creation():
    engine = get_dispatch_engine()
    session = engine.create_session(caller_id="CALLER-555")
    assert session.session_id is not None
    assert session.caller_id == "CALLER-555"
    assert session.state == DispatchSessionState.LISTENING


@pytest.mark.asyncio
async def test_dispatch_engine_record_transcript():
    engine = get_dispatch_engine()
    session = engine.create_session()
    await engine.record_transcript(
        session_id=session.session_id,
        speaker="caller",
        text="Need emergency help at Pier 44",
        is_final=True
    )
    assert len(session.transcript_history) == 1
    assert session.transcript_history[0]["text"] == "Need emergency help at Pier 44"


@pytest.mark.asyncio
async def test_run_autonomous_dispatch_pipeline_end_to_end():
    engine = get_dispatch_engine()
    session = engine.create_session()

    result = await engine.run_autonomous_dispatch_pipeline(
        session_id=session.session_id,
        location_text="I-95 Northbound at Mile Marker 42",
        incident_description="Overturned chemical tanker leaking gas with crushed vehicle",
        hazards=["toxic_chemical_spill", "trapped_personnel"]
    )

    assert result["status"] == "PIPELINE_COMPLETE"
    assert result["ticket_id"].startswith("TICK-")
    assert len(result["assigned_units"]) > 0
    assert result["total_tools_executed"] >= 5
    assert session.state == DispatchSessionState.UNITS_DISPATCHED
