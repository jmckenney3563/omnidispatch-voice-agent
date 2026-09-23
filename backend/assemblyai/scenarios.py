"""
Realistic Emergency Dispatch Scenarios with millisecond timing,
dialogue turns, mock audio waveform generation, and tool triggers.
"""
import math
import struct
import base64
from typing import List, Dict, Any, Optional


def generate_pcm_audio_chunk(
    frequency_hz: float = 440.0,
    duration_seconds: float = 0.5,
    sample_rate: int = 16000,
    amplitude: float = 0.4,
    noise_level: float = 0.03
) -> bytes:
    """
    Generates 16kHz 16-bit Mono Linear PCM audio bytes with voice formant harmonics
    and background emergency radio static for realistic visualization.
    """
    total_samples = int(sample_rate * duration_seconds)
    audio_bytes = bytearray()

    import random
    rng = random.Random(int(frequency_hz * 100))

    for i in range(total_samples):
        t = float(i) / sample_rate
        # Voice envelope: soft attack and release
        envelope = 1.0
        attack_len = int(sample_rate * 0.05)
        release_len = int(sample_rate * 0.05)
        if i < attack_len:
            envelope = i / attack_len
        elif i > total_samples - release_len:
            envelope = (total_samples - i) / release_len

        # Formant-like harmonic sum (fundamental + 1st harmonic + 2nd harmonic)
        f1 = frequency_hz
        f2 = frequency_hz * 1.6
        f3 = frequency_hz * 2.4
        sig = (
            0.6 * math.sin(2.0 * math.pi * f1 * t) +
            0.3 * math.sin(2.0 * math.pi * f2 * t) +
            0.15 * math.sin(2.0 * math.pi * f3 * t)
        )
        # Add subtle radio static noise
        noise = (rng.random() * 2.0 - 1.0) * noise_level
        sample_float = (sig + noise) * amplitude * envelope
        # Clamp to 16-bit signed integer range (-32768 to 32767)
        sample_int = int(max(-32768, min(32767, sample_float * 32767.0)))
        audio_bytes.extend(struct.pack("<h", sample_int))

    return bytes(audio_bytes)


SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "scenario-1",
        "title": "Interstate 95 Chemical Tanker Collision",
        "category": "HAZMAT & MULTI-VEHICLE HIGHWAY COLLISION",
        "severity": "CRITICAL",
        "location": "Interstate 95 Northbound at Mile Marker 42, North Corridor Overpass",
        "sector": "Highway-North",
        "description": "Multi-car collision involving pressurized hazardous chemical tanker with active vapor leak and trapped occupants.",
        "recommended_units": ["HAZMAT_UNIT", "HEAVY_RESCUE", "EMS_AMBULANCE", "POLICE_PATROL"],
        "hazards": ["toxic_chemical_spill", "trapped_personnel", "high_speed_traffic"],
        "turns": [
            {
                "turn_index": 0,
                "speaker": "caller",
                "speaker_name": "Caller [911-Cell]",
                "start_ms": 500,
                "duration_ms": 3200,
                "text": "911 emergency! Massive collision on I-95 Northbound right at Mile Marker 42! A chemical tanker truck flipped, yellow vapor is leaking everywhere, and two cars are crushed!",
                "tone": "PANICKED",
                "frequency": 280.0,
                "amplitude": 0.65
            },
            {
                "turn_index": 1,
                "speaker": "agent",
                "speaker_name": "OmniDispatch Voice AI",
                "start_ms": 4100,
                "duration_ms": 2800,
                "text": "OmniDispatch receiving. Location triangulated to I-95 Mile 42. Are there motorists trapped, and can you see UN hazard placard numbers on the tanker?",
                "tone": "CALM_AUTHORITATIVE",
                "frequency": 165.0,
                "amplitude": 0.50
            },
            {
                "turn_index": 2,
                "speaker": "caller",
                "speaker_name": "Caller [911-Cell]",
                "start_ms": 7200,
                "duration_ms": 3000,
                "text": "Yes! The sedan driver is pinned under the tanker chassis, completely unconscious! The tanker has placard 1017 chlorine gas! It's choking everyone, people are running!",
                "tone": "URGENT",
                "frequency": 310.0,
                "amplitude": 0.75
            },
            {
                "turn_index": 3,
                "speaker": "agent",
                "speaker_name": "OmniDispatch Voice AI",
                "start_ms": 10600,
                "duration_ms": 3500,
                "text": "Critical Code-1 Hazmat Chlorine Protocol activated. Hazmat-7 and Rescue-3 dispatched with ALS Medic-101. Highway Patrol-204 closing all northbound lanes. Move immediately upwind and stay 500 feet back.",
                "tone": "DIRECTIVE",
                "frequency": 165.0,
                "amplitude": 0.50
            }
        ]
    },
    {
        "id": "scenario-2",
        "title": "Pier 44 Industrial Warehouse 3-Alarm Blaze",
        "category": "COMMERCIAL STRUCTURE FIRE & RESCUE",
        "severity": "CRITICAL",
        "location": "Pier 44 Logistics Warehouse, 820 Dock Street",
        "sector": "Industrial-Port",
        "description": "Lithium-ion battery storage warehouse fire with structural roof collapse threat and three workers trapped in loading bay 4.",
        "recommended_units": ["FIRE_ENGINE", "AERIAL_LADDER", "HEAVY_RESCUE", "EMS_AMBULANCE"],
        "hazards": ["structure_fire", "trapped_personnel", "lithium_battery_thermal_runaway"],
        "turns": [
            {
                "turn_index": 0,
                "speaker": "caller",
                "speaker_name": "Warehouse Safety Supervisor",
                "start_ms": 500,
                "duration_ms": 3100,
                "text": "Mayday! Pier 44 logistics warehouse, 820 Dock Street! Tier-3 lithium battery racks caught fire, heavy toxic smoke is filling the bays, and three workers are cut off in Bay 4!",
                "tone": "DISTRESSED",
                "frequency": 260.0,
                "amplitude": 0.70
            },
            {
                "turn_index": 1,
                "speaker": "agent",
                "speaker_name": "OmniDispatch Voice AI",
                "start_ms": 4000,
                "duration_ms": 2600,
                "text": "Pier 44 Dock Street identified. Are fire sprinkler risers active, and is the Bay 4 roll-down security door locked?",
                "tone": "CALM_AUTHORITATIVE",
                "frequency": 165.0,
                "amplitude": 0.50
            },
            {
                "turn_index": 2,
                "speaker": "caller",
                "speaker_name": "Warehouse Safety Supervisor",
                "start_ms": 6900,
                "duration_ms": 3200,
                "text": "Sprinklers failed due to blast pressure! The bay doors are warped shut by thermal buckling! Roof truss ventilation is showing heavy orange flame! They need hydraulic extrication now!",
                "tone": "CRITICAL_PANIC",
                "frequency": 295.0,
                "amplitude": 0.80
            },
            {
                "turn_index": 3,
                "speaker": "agent",
                "speaker_name": "OmniDispatch Voice AI",
                "start_ms": 10500,
                "duration_ms": 3600,
                "text": "3-Alarm Structural Box Alarm dispatched. Engine-4 and Ladder-12 responding with master water streams and 100-foot platform. Rescue-3 en route with hydraulic saws for Bay 4 breach.",
                "tone": "DIRECTIVE",
                "frequency": 165.0,
                "amplitude": 0.50
            }
        ]
    },
    {
        "id": "scenario-3",
        "title": "Alpine Pass Cold-Chain Biologics Rescue",
        "category": "HIGH-VALUE PHARMACEUTICAL CRYOGENIC CRISIS",
        "severity": "HIGH",
        "location": "Route 9 Alpine Pass, Mile Post 18 Mountain Cut",
        "sector": "Northern-Valley",
        "description": "Blizzard breakdown of refrigerated carrier holding 20,000 oncology biologics at risk of critical thermal degradation within 30 minutes.",
        "recommended_units": ["COLD_CHAIN_REFRIGERATED", "LOGISTICS_SUPPORT", "POLICE_PATROL"],
        "hazards": ["temperature_critical", "severe_blizzard_icing", "remote_pass_stranding"],
        "turns": [
            {
                "turn_index": 0,
                "speaker": "caller",
                "speaker_name": "Carrier Driver BioRoute-9",
                "start_ms": 500,
                "duration_ms": 3300,
                "text": "OmniDispatch, this is BioTransport-12 stranded on Route 9 Alpine Pass at Mile Post 18. Whiteout blizzard conditions, my engine seized, and the primary cryogenic chiller head has failed!",
                "tone": "ANXIOUS",
                "frequency": 240.0,
                "amplitude": 0.60
            },
            {
                "turn_index": 1,
                "speaker": "agent",
                "speaker_name": "OmniDispatch Voice AI",
                "start_ms": 4200,
                "duration_ms": 2700,
                "text": "OmniDispatch Cold-Chain Logistics. Connecting to your trailer telemetry. Confirming twenty thousand oncology vials. What is your current cargo core temperature?",
                "tone": "CALM_AUTHORITATIVE",
                "frequency": 165.0,
                "amplitude": 0.50
            },
            {
                "turn_index": 2,
                "speaker": "caller",
                "speaker_name": "Carrier Driver BioRoute-9",
                "start_ms": 7300,
                "duration_ms": 3100,
                "text": "Chamber temp is negative 62 Celsius and climbing 0.4 degrees every two minutes! If we cross negative 50 Celsius, the entire batch spoils! Snowdrifts are blocking the mountain pass!",
                "tone": "URGENT",
                "frequency": 270.0,
                "amplitude": 0.70
            },
            {
                "turn_index": 3,
                "speaker": "agent",
                "speaker_name": "OmniDispatch Voice AI",
                "start_ms": 10800,
                "duration_ms": 3400,
                "text": "Priority Cold-Chain Emergency dispatched. ColdChain-09 mobile deep-freeze transfer truck and Patrol-204 plow escort en route with Code-3 emergency clearance. ETA 9 minutes.",
                "tone": "DIRECTIVE",
                "frequency": 165.0,
                "amplitude": 0.50
            }
        ]
    }
]


def get_all_scenarios() -> List[Dict[str, Any]]:
    return SCENARIOS


def get_scenario_by_id(scenario_id: str) -> Optional[Dict[str, Any]]:
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return s
    return None
