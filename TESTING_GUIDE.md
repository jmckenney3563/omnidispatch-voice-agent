# OmniDispatch: Quality Assurance & Testing Guide

This guide provides step-by-step instructions for verifying and testing the **OmniDispatch Autonomous Emergency & Fleet Logistics Voice Agent**. It covers automated unit/integration tests (`pytest`), REST API endpoint validation via `curl`, live WebSocket streaming verification, manual UI scenario walkthroughs, and environment configuration.

---

## Table of Contents

- [1. Quick Verification (Pytest Suite)](#1-quick-verification-pytest-suite)
- [2. Environment Variable Configuration](#2-environment-variable-configuration)
- [3. REST API Step-by-Step Verification](#3-rest-api-step-by-step-verification)
  - [3.1 System Health & Engine Status (`/api/health`)](#31-system-health--engine-status-apihealth)
  - [3.2 Fleet Operations & Roster (`/api/fleet`)](#32-fleet-operations--roster-apifleet)
  - [3.3 Emergency Scenarios (`/api/scenarios`)](#33-emergency-scenarios-apiscenarios)
  - [3.4 JSON Schema Tools (`/api/tools`)](#34-json-schema-tools-apitools)
  - [3.5 Dynamic Tool Invocation (`/api/dispatch/tool-execute`)](#35-dynamic-tool-invocation-apidispatchtool-execute)
  - [3.6 Dispatch Tickets Vault (`/api/tickets`)](#36-dispatch-tickets-vault-apitickets)
  - [3.7 Voice Call Initiation (`/api/dispatch/call`)](#37-voice-call-initiation-apidispatchcall)
- [4. WebSocket Streaming Verification (`/ws/dispatch`)](#4-websocket-streaming-verification-wsdispatch)
  - [4.1 Python WebSocket Verification Script](#41-python-websocket-verification-script)
  - [4.2 Verification via `wscat` / Browser DevTools](#42-verification-via-wscat--browser-devtools)
- [5. Interactive Browser UI Walkthrough](#5-interactive-browser-ui-walkthrough)
  - [Walkthrough 1: Automated Scenario 1 (I-95 Hazmat)](#walkthrough-1-automated-scenario-1-i-95-hazmat)
  - [Walkthrough 2: Automated Scenario 2 (Pier 44 3-Alarm Blaze)](#walkthrough-2-automated-scenario-2-pier-44-3-alarm-blaze)
  - [Walkthrough 3: Automated Scenario 3 (Alpine Pass Cold-Chain)](#walkthrough-3-automated-scenario-3-alpine-pass-cold-chain)
  - [Walkthrough 4: Live Browser Mic Streaming Mode](#walkthrough-4-live-browser-mic-streaming-mode)
- [6. Troubleshooting & Diagnostics](#6-troubleshooting--diagnostics)

---

## 1. Quick Verification (Pytest Suite)

OmniDispatch includes a 29-test comprehensive test suite validating all backend components without requiring external API network access.

### Run All 29 Passing Tests

```bash
cd /home/ddso/Projects/omnidispatch-voice-agent

# Ensure virtual environment is activated
source .venv/bin/activate

# Execute pytest with verbose output
pytest -v
```

### Expected Output Summary

```text
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1
rootdir: /home/ddso/Projects/omnidispatch-voice-agent
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1, asyncio-1.4.0
collected 29 items

tests/test_api_and_websocket.py::test_api_health PASSED                  [  3%]
tests/test_api_and_websocket.py::test_api_fleet_endpoints PASSED         [  6%]
tests/test_api_and_websocket.py::test_api_fleet_reset PASSED             [ 10%]
tests/test_api_and_websocket.py::test_api_scenarios_endpoints PASSED     [ 13%]
tests/test_api_and_websocket.py::test_api_tools_endpoint PASSED          [ 17%]
tests/test_api_and_websocket.py::test_api_tool_execute_endpoint PASSED   [ 20%]
tests/test_api_and_websocket.py::test_api_create_manual_ticket_and_list PASSED [ 24%]
tests/test_api_and_websocket.py::test_api_dispatch_call_initiate PASSED  [ 27%]
tests/test_api_and_websocket.py::test_websocket_connection_and_ping PASSED [ 31%]
tests/test_assemblyai_stream.py::test_calculate_pcm_energy_silence PASSED [ 34%]
tests/test_assemblyai_stream.py::test_generate_pcm_audio_chunk PASSED    [ 37%]
tests/test_assemblyai_stream.py::test_scenarios_structure PASSED         [ 41%]
tests/test_assemblyai_stream.py::test_get_scenario_by_id PASSED          [ 44%]
tests/test_assemblyai_stream.py::test_assemblyai_simulator_run PASSED    [ 48%]
tests/test_dispatch_tools.py::test_tools_schema_count_and_format PASSED  [ 51%]
tests/test_dispatch_tools.py::test_locate_caller_and_incident_known PASSED [ 55%]
tests/test_dispatch_tools.py::test_locate_caller_and_incident_fallback PASSED [ 58%]
tests/test_dispatch_tools.py::test_lookup_fleet_units PASSED             [ 62%]
tests/test_dispatch_tools.py::test_calculate_incident_route PASSED       [ 65%]
tests/test_dispatch_tools.py::test_assess_incident_severity PASSED       [ 68%]
tests/test_dispatch_tools.py::test_assign_dispatch_ticket PASSED         [ 72%]
tests/test_dispatch_tools.py::test_send_driver_notification PASSED       [ 75%]
tests/test_dispatch_tools.py::test_execute_tool_dynamic PASSED           [ 79%]
tests/test_fleet_engine.py::test_fleet_database_initialization PASSED    [ 82%]
tests/test_fleet_engine.py::test_haversine_distance_calculation PASSED   [ 86%]
tests/test_fleet_engine.py::test_eta_calculation PASSED                  [ 89%]
tests/test_fleet_engine.py::test_dispatch_engine_session_creation PASSED [ 93%]
tests/test_fleet_engine.py::test_dispatch_engine_record_transcript PASSED [ 96%]
tests/test_fleet_engine.py::test_run_autonomous_dispatch_pipeline_end_to_end PASSED [100%]

======================== 29 passed in 1.24s ========================
```

### Module Breakdown

- **`test_api_and_websocket.py` (9 tests):** Validates REST contract, CRUD operations, ticket persistence, schema discovery, and WebSocket connection handshake.
- **`test_assemblyai_stream.py` (5 tests):** Validates 16kHz PCM energy calculations, harmonic audio waveform generation, scenario data models, and simulator callbacks.
- **`test_dispatch_tools.py` (9 tests):** Validates the 6 JSON schema tools, fallback geocoding, severity assessment rules, driver MDT notifications, and dynamic execution timing benchmarks.
- **`test_fleet_engine.py` (6 tests):** Validates Haversine spherical distance formulas, emergency traffic ETA algorithms, session state transitions, transcript buffering, and end-to-end autonomous 6-tool execution cascades.

---

## 2. Environment Variable Configuration

OmniDispatch is designed with **dual-mode operational readiness**:

1. **Zero-Config Simulation Mode (Default):** Runs immediately without external API keys. Generates realistic 16kHz audio waveforms with formant harmonics and simulates AssemblyAI Universal-3 Pro real-time streaming transcripts.
2. **Live AssemblyAI WebSocket Mode:** Streams live audio from your microphone or audio interface directly to `wss://api.assemblyai.com/v2/realtime/ws`.

### Setup Instructions

```bash
# 1. Copy the example configuration template
cp .env.example .env

# 2. (Optional) Provide your AssemblyAI API Key in .env
# Open .env in your text editor and set:
# ASSEMBLYAI_API_KEY=your_actual_key_from_assemblyai_dashboard
```

### Configuration Options Reference

```ini
# AssemblyAI API Configuration
ASSEMBLYAI_API_KEY=               # Empty = Simulation Mode; Key = Live Realtime API
ASSEMBLYAI_REALTIME_URL=wss://api.assemblyai.com/v2/realtime/ws

# Audio Telemetry
AUDIO_SAMPLE_RATE=16000           # Linear PCM sampling frequency (16kHz recommended)
AUDIO_CHANNELS=1                  # 1 = Mono audio
AUDIO_CHUNK_MS=100                # WebSocket chunking interval

# Turn-Taking & Voice Activity Detection (VAD)
VAD_SILENCE_THRESHOLD_MS=750      # Silence window (ms) to detect caller turn completion
VAD_ENERGY_THRESHOLD=0.015        # Normalized RMS threshold separating voice from background noise
AUTO_TOOL_EXECUTION=true          # Autonomous 6-tool pipeline execution flag

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

---

## 3. REST API Step-by-Step Verification

Start the backend server in terminal 1:

```bash
cd /home/ddso/Projects/omnidispatch-voice-agent
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open Swagger UI in your browser at `http://localhost:8000/docs`, or use the `curl` commands below in terminal 2.

### 3.1 System Health & Engine Status (`/api/health`)

Verify server readiness and AssemblyAI mode:

```bash
curl -s http://localhost:8000/api/health | jq .
```

**Expected JSON Response:**
```json
{
  "status": "ONLINE",
  "app_name": "OmniDispatch - Autonomous Emergency & Fleet Logistics Voice Agent",
  "version": "1.0.0",
  "assemblyai_status": "HIGH_FIDELITY_SIMULATION",
  "assemblyai_model": "Universal-3 Pro Realtime STT",
  "sample_rate_hz": 16000,
  "vad_silence_threshold_ms": 750,
  "tools_loaded": 6
}
```

> *Note: If `ASSEMBLYAI_API_KEY` is provided, `assemblyai_status` will report `"LIVE_API_READY"`.*

---

### 3.2 Fleet Operations & Roster (`/api/fleet`)

List all 9 emergency fleet vehicles:

```bash
curl -s http://localhost:8000/api/fleet | jq '.[0:3]'
```

**Expected JSON Response:**
```json
[
  {
    "id": "unit-101",
    "callsign": "Medic-101",
    "type": "EMS_AMBULANCE",
    "status": "AVAILABLE",
    "coordinates": {
      "lat": 40.758,
      "lng": -73.9855,
      "sector": "Metro-North",
      "address": "Station 12, Broadway & 48th"
    },
    "speed_mph": 0.0,
    "capabilities": [
      "ALS (Advanced Life Support)",
      "Trauma",
      "Defibrillator",
      "Lucas Chest Compression"
    ],
    "eta_minutes": null,
    "assigned_ticket_id": null,
    "contact_freq": "155.340 MHz (EMS-1)",
    "crew_count": 2
  }
]
```

Query a specific unit:
```bash
curl -s http://localhost:8000/api/fleet/unit-107 | jq .
```

Reset fleet and active tickets to clean default state:
```bash
curl -s -X POST http://localhost:8000/api/fleet/reset | jq .
```

---

### 3.3 Emergency Scenarios (`/api/scenarios`)

Verify that the 3 realistic emergency scenarios are loaded:

```bash
curl -s http://localhost:8000/api/scenarios | jq '.[].title'
```

**Expected Output:**
```text
"Interstate 95 Chemical Tanker Collision"
"Pier 44 Industrial Warehouse 3-Alarm Blaze"
"Alpine Pass Cold-Chain Biologics Rescue"
```

Fetch details for Scenario 1:
```bash
curl -s http://localhost:8000/api/scenarios/scenario-1 | jq '{title, severity, sector, turns_count: (.turns | length)}'
```

---

### 3.4 JSON Schema Tools (`/api/tools`)

Inspect the 6 registered dispatch tools:

```bash
curl -s http://localhost:8000/api/tools | jq '{count, tool_names: [.tools[].function.name]}'
```

**Expected Output:**
```json
{
  "count": 6,
  "tool_names": [
    "locate_caller_and_incident",
    "lookup_fleet_units",
    "calculate_incident_route",
    "assess_incident_severity",
    "assign_dispatch_ticket",
    "send_driver_notification"
  ]
}
```

---

### 3.5 Dynamic Tool Invocation (`/api/dispatch/tool-execute`)

You can test any of the 6 tools directly with custom arguments:

#### Test Tool 1 (`locate_caller_and_incident`):
```bash
curl -s -X POST http://localhost:8000/api/dispatch/tool-execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "locate_caller_and_incident",
    "arguments": {
      "raw_location_text": "I-95 Northbound near Mile Marker 42 overpass"
    }
  }' | jq .
```

**Expected Result:**
```json
{
  "tool_name": "locate_caller_and_incident",
  "result": {
    "status": "LOCATED",
    "resolved_address": "Interstate 95 Northbound at Mile Marker 42, North Corridor Overpass",
    "lat": 40.7852,
    "lng": -73.9621,
    "sector": "Highway-North",
    "risk_zone": "High-Speed Interstate / Hazmat Arterial"
  },
  "duration_ms": 0.45
}
```

#### Test Tool 4 (`assess_incident_severity`):
```bash
curl -s -X POST http://localhost:8000/api/dispatch/tool-execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "assess_incident_severity",
    "arguments": {
      "incident_description": "Tanker flipped, yellow chlorine gas cloud, unconscious driver trapped under chassis",
      "hazards_reported": ["toxic_chemical_spill", "trapped_personnel"],
      "caller_stress_level": "CRITICAL"
    }
  }' | jq .result
```

**Expected Result:**
```json
{
  "status": "ASSESSED",
  "severity": "CRITICAL",
  "incident_code": "CODE-1-CRITICAL-MULTIAGENCY",
  "dispatch_urgency": "IMMEDIATE_LIFE_SAFETY",
  "recommended_unit_types": [
    "FIRE_ENGINE",
    "EMS_AMBULANCE",
    "HAZMAT_UNIT",
    "HEAVY_RESCUE"
  ]
}
```

---

### 3.6 Dispatch Tickets Vault (`/api/tickets`)

List active tickets:
```bash
curl -s http://localhost:8000/api/tickets | jq .
```

Manually mint a ticket via Operations Override:
```bash
curl -s -X POST http://localhost:8000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "incident_type": "STRUCTURAL_COLLAPSE",
    "severity": "CRITICAL",
    "description": "Scaffolding collapse with multiple injuries",
    "address": "450 7th Ave, Manhattan",
    "lat": 40.7510,
    "lng": -73.9890,
    "sector": "Metro-Midtown",
    "assigned_units": ["unit-103", "unit-101"]
  }' | jq .
```

---

### 3.7 Voice Call Initiation (`/api/dispatch/call`)

Initialize a call session and obtain the WebSocket streaming URL:

```bash
curl -s -X POST http://localhost:8000/api/dispatch/call \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "scenario-1", "caller_phone": "911-555-0199"}' | jq .
```

**Expected Result:**
```json
{
  "status": "SESSION_INITIALIZED",
  "session_id": "...",
  "caller_id": "911-555-0199",
  "scenario_id": "scenario-1",
  "live_mode": false,
  "websocket_url": "/ws/dispatch?session_id=...&scenario_id=scenario-1"
}
```

---

## 4. WebSocket Streaming Verification (`/ws/dispatch`)

### 4.1 Python WebSocket Verification Script

Run this quick test script to verify bi-directional message exchange, scenario execution, and real-time audio telemetry:

```python
# test_ws.py
import asyncio
import json
import websockets

async def verify_websocket():
    uri = "ws://localhost:8000/ws/dispatch?scenario_id=none"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as ws:
        # Wait for system notification
        welcome = await ws.recv()
        print(f"Server Initial Event: {welcome}")

        # Send ping
        await ws.send(json.dumps({"action": "ping"}))
        pong = await ws.recv()
        print(f"Ping/Pong Response: {pong}")

        # Trigger Scenario 1
        print("Triggering Scenario 1 via WebSocket...")
        await ws.send(json.dumps({"action": "start_scenario", "scenario_id": "scenario-1"}))

        # Listen for first 8 events
        for _ in range(8):
            raw = await ws.recv()
            event = json.loads(raw)
            print(f"Stream Event: {event.get('event')} | Speaker: {event.get('speaker', 'N/A')}")

        print("WebSocket streaming verified successfully!")

asyncio.run(verify_websocket())
```

Execute:
```bash
python3 test_ws.py
```

### 4.2 Verification via `wscat` / Browser DevTools

If you have `wscat` installed:

```bash
wscat -c "ws://localhost:8000/ws/dispatch?scenario_id=scenario-1"
```

Observe streaming partial transcripts, audio waveform packets, and tool execution events streaming in real time.

---

## 5. Interactive Browser UI Walkthrough

Open `http://localhost:8000` in Google Chrome or Mozilla Firefox.

### Walkthrough 1: Automated Scenario 1 (I-95 Hazmat)

1. **Select Scenario:** In the top scenario bar, verify that **"Interstate 95 Chemical Tanker Collision"** is selected (cyan highlighted).
2. **Trigger Emergency Call:** Click the red **"TRIGGER EMERGENCY CALL"** button.
3. **Observe Acoustic Telemetry:**
   - The **Acoustic Telemetry Canvas** immediately renders a dynamic audio waveform.
   - The indicator switches to `CALLER [911]` with an amber pulsing glow.
   - Decibel level tracks between `-15 dB` and `-35 dB`.
4. **Observe Universal-3 Pro STT Transcript:**
   - Real-time word-by-word streaming partial text displays in the pulsing cyan bubble.
   - Finalized turns show latency indicators (`~58ms STT`) and high confidence scores (`99%`).
5. **Observe VAD Turn-Taking & Tool Cascade:**
   - After the caller's first statement finishes, the VAD indicator flashes green (`VAD SILENCE`).
   - The system alert banner announces: *"Autonomous Dispatch Triggered: Turn complete. VAD silence detected. Executing 6-tool pipeline..."*
   - In the **MCP Tool Inspector**, watch the 6 tools execute in rapid succession:
     - `locate_caller_and_incident`
     - `assess_incident_severity`
     - `lookup_fleet_units`
     - `calculate_incident_route`
     - `assign_dispatch_ticket`
     - `send_driver_notification`
6. **Observe Tactical Sector Radar:**
   - A red flashing distress beacon appears at Sector North (`TARGET: Highway-North`).
   - Responding units (`Medic-101`, `Hazmat-7`, `Patrol-204`) switch to amber pulsing markers with dashed trajectory vectors pointing toward the incident.
   - Click on any unit marker to view crew count, radio frequency, and calculated ETA.
7. **Observe Tickets Vault & Fleet Board:**
   - A new ticket `TICK-XXXX` appears in the Tickets Vault marked `CRITICAL`.
   - The Fleet Status Roster updates unit statuses to `EN_ROUTE` with live ETA counters.

---

### Walkthrough 2: Automated Scenario 2 (Pier 44 3-Alarm Blaze)

1. Click **"Reset Ops"** in the top navigation to clear active incidents.
2. Select **"Pier 44 Industrial Warehouse 3-Alarm Blaze"**.
3. Click **"TRIGGER EMERGENCY CALL"**.
4. Observe the structural fire protocol activation:
   - Tool `assess_incident_severity` identifies `structure_fire`, `trapped_personnel`, and `lithium_battery_thermal_runaway`.
   - Tool `lookup_fleet_units` dispatches `Engine-4` (1500 GPM pumper), `Ladder-12` (100ft aerial), and `Rescue-3` (heavy extrication jaws).
   - Radar map projects emergency corridors into Sector West (Port).

---

### Walkthrough 3: Automated Scenario 3 (Alpine Pass Cold-Chain)

1. Click **"Reset Ops"**.
2. Select **"Alpine Pass Cold-Chain Biologics Rescue"**.
3. Click **"TRIGGER EMERGENCY CALL"**.
4. Observe cold-chain logistics protocol activation:
   - Evaluates sub-zero cryogenic risk (-62°C oncology vials approaching -50°C spoilage threshold).
   - Dispatches `ColdChain-09` (-80°C deep freeze chamber) with `Patrol-204` snow plow escort.
   - Calculates 8.9-minute mountain pass emergency ETA.

---

### Walkthrough 4: Live Browser Mic Streaming Mode

1. Ensure `ASSEMBLYAI_API_KEY` is configured in `.env` (or run in simulation mode).
2. Click **"LIVE MIC MODE"**.
3. Grant browser microphone permissions when prompted.
4. Speak into your microphone:  
   *"There is a major chemical spill on Interstate 95 Northbound at Mile Marker 42!"*
5. Watch your voice generate live PCM audio chunks streamed across the WebSocket.
6. As you pause speaking for >750ms, the VAD triggers caller turn completion, and OmniDispatch autonomously runs the 6-tool routing pipeline on your spoken words.

---

## 6. Troubleshooting & Diagnostics

| Symptom | Probable Cause | Resolution |
|---|---|---|
| **Frontend displays fallback JSON at `http://localhost:8000/`** | Frontend assets have not been compiled into `frontend/dist`. | Run `cd frontend && npm install && npm run build` to generate the production bundle. |
| **`ASSEMBLYAI_API_KEY` invalid or unauthorized** | Incorrect key entered or trial limits exceeded. | Verify your key at [AssemblyAI Dashboard](https://www.assemblyai.com/dashboard). OmniDispatch will automatically fall back to simulation mode if the key is missing or invalid. |
| **Microphone permission error in browser** | Browser denied audio access or non-secure origin. | Ensure accessing via `http://localhost:8000` (localhost is treated as secure context) and grant microphone access in browser site settings. |
| **Port 8000 already in use** | Another instance of FastAPI or Docker container is running. | Run `lsof -i :8000` or `kill -9 $(lsof -t -i:8000)` or change port via `uvicorn backend.main:app --port 8001`. |
| **Pytest warning about `starlette.testclient`** | Starlette deprecation note regarding `httpx`. | Benign warning; does not affect test validity or pass status (all 29 tests pass). |
