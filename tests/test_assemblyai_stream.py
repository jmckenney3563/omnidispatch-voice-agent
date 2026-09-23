"""
Tests for AssemblyAI audio processing, streaming simulation, and VAD calculations.
"""
import pytest
import asyncio
from backend.assemblyai.client import calculate_pcm_energy, AssemblyAISimulator
from backend.assemblyai.scenarios import (
    generate_pcm_audio_chunk,
    get_all_scenarios,
    get_scenario_by_id,
    SCENARIOS
)


def test_calculate_pcm_energy_silence():
    # 0 bytes or silence
    assert calculate_pcm_energy(b"") == 0.0
    silence = b"\x00\x00" * 100
    assert calculate_pcm_energy(silence) == 0.0


def test_generate_pcm_audio_chunk():
    # 16000 sample rate, 0.1s -> 1600 samples -> 3200 bytes
    pcm = generate_pcm_audio_chunk(frequency_hz=300.0, duration_seconds=0.1, sample_rate=16000)
    assert len(pcm) == 3200
    energy = calculate_pcm_energy(pcm)
    assert energy > 0.01  # non-silent


def test_scenarios_structure():
    scenarios = get_all_scenarios()
    assert len(scenarios) >= 3
    for s in scenarios:
        assert "id" in s
        assert "title" in s
        assert "turns" in s
        assert len(s["turns"]) >= 4
        # Verify turn fields
        for t in s["turns"]:
            assert "speaker" in t
            assert "text" in t
            assert "duration_ms" in t


def test_get_scenario_by_id():
    s1 = get_scenario_by_id("scenario-1")
    assert s1 is not None
    assert s1["id"] == "scenario-1"
    assert "Chemical Tanker" in s1["title"]

    invalid = get_scenario_by_id("non-existent")
    assert invalid is None


@pytest.mark.asyncio
async def test_assemblyai_simulator_run():
    partials = []
    finals = []
    packets = []
    turns = []

    async def on_partial(text, conf):
        partials.append(text)

    async def on_final(text, conf):
        finals.append(text)

    async def on_packet(b64, energy, speaker):
        packets.append((energy, speaker))

    async def on_turn(speaker, status):
        turns.append((speaker, status))

    # Fast forward simulator (10x speed)
    sim = AssemblyAISimulator(
        on_partial=on_partial,
        on_final=on_final,
        on_audio_packet=on_packet,
        on_turn_change=on_turn,
        speed_multiplier=5.0
    )

    # Run first scenario briefly or run short turn
    task = asyncio.create_task(sim.run_scenario("scenario-1"))
    await asyncio.sleep(0.6)
    sim.stop()
    await asyncio.gather(task, return_exceptions=True)

    assert len(packets) > 0
    assert len(turns) > 0
