"""
Voice Agent Orchestrator: Turn-Taking, VAD Silence Detection, and Conversation Engine.
Coordinates between AssemblyAI STT, VAD, and Autonomous Dispatch Pipeline.
"""
import time
import base64
import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timezone
from backend.config import get_settings
from backend.dispatch.engine import get_dispatch_engine
from backend.assemblyai.scenarios import (
    get_scenario_by_id,
    generate_pcm_audio_chunk,
    SCENARIOS
)
from backend.assemblyai.client import (
    AssemblyAIRealtimeClient,
    AssemblyAISimulator,
    calculate_pcm_energy
)

logger = logging.getLogger("omnidispatch.voice_agent")


class VoiceAgentSession:
    """
    Manages a single conversational emergency dispatch session.
    Tracks speaker turns, VAD, STT transcripts, and tool execution triggers.
    """

    def __init__(
        self,
        session_id: str,
        on_event: Callable[[str, Dict[str, Any]], Any],
        live_mode: bool = False
    ):
        self.session_id = session_id
        self.on_event = on_event
        self.live_mode = live_mode
        self.settings = get_settings()
        self.engine = get_dispatch_engine()

        # State tracking
        self.active_speaker = "system"
        self.is_caller_speaking = False
        self.last_audio_activity_time = time.time()
        self.current_utterance_text = ""
        self.accumulated_caller_text: List[str] = []
        self.pipeline_executed = False

        # Live STT client & Simulator
        self.stt_client: Optional[AssemblyAIRealtimeClient] = None
        self.simulator: Optional[AssemblyAISimulator] = None
        self._vad_task: Optional[asyncio.Task] = None
        self.is_active = True

    async def start_scenario(self, scenario_id: str):
        """Starts a simulated scenario session."""
        scenario = get_scenario_by_id(scenario_id) or SCENARIOS[0]
        logger.info(f"Initiating scenario session: {scenario['id']} ({scenario['title']})")

        # Notify frontend
        await self.emit("session_started", {
            "session_id": self.session_id,
            "mode": "simulation",
            "scenario": {
                "id": scenario["id"],
                "title": scenario["title"],
                "severity": scenario["severity"],
                "sector": scenario["sector"],
                "location": scenario["location"]
            }
        })

        self.simulator = AssemblyAISimulator(
            on_partial=self._on_sim_partial,
            on_final=self._on_sim_final,
            on_audio_packet=self._on_sim_audio_packet,
            on_turn_change=self._on_sim_turn_change,
            speed_multiplier=self.settings.simulation_speed_multiplier
        )

        # Run scenario in background task
        asyncio.create_task(self._run_scenario_orchestrator(scenario))

    async def _run_scenario_orchestrator(self, scenario: Dict[str, Any]):
        """Runs the simulator and triggers automated dispatch tools at appropriate turns."""
        turns = scenario["turns"]

        for idx, turn in enumerate(turns):
            if not self.is_active:
                break

            speaker = turn["speaker"]
            text = turn["text"]
            self.active_speaker = speaker

            # Emit turn start
            await self.emit("turn_status", {
                "speaker": speaker,
                "status": "SPEAKING",
                "text_preview": text[:40] + "..."
            })

            # Stream speech audio and progressive transcripts
            words = text.split(" ")
            duration_s = turn["duration_ms"] / 1000.0
            num_steps = max(4, min(len(words), 10))
            step_interval = duration_s / num_steps

            for step in range(num_steps):
                if not self.is_active:
                    break

                end_w = int(((step + 1) / num_steps) * len(words))
                partial_txt = " ".join(words[:end_w])

                # Audio packet
                pcm = generate_pcm_audio_chunk(
                    frequency_hz=turn.get("frequency", 220.0),
                    duration_seconds=min(0.2, step_interval),
                    amplitude=turn.get("amplitude", 0.5)
                )
                energy = calculate_pcm_energy(pcm)
                b64_audio = base64.b64encode(pcm).decode("utf-8")

                await self.emit("audio_waveform", {
                    "speaker": speaker,
                    "energy": energy,
                    "sample_rate": 16000,
                    "audio_b64": b64_audio
                })

                if step < num_steps - 1:
                    await self.emit("transcript_partial", {
                        "speaker": speaker,
                        "speaker_name": turn.get("speaker_name", speaker),
                        "text": partial_txt,
                        "confidence": 0.94
                    })
                else:
                    # Final transcript for turn
                    latency = round(time.perf_counter() * 10 % 100 + 40, 1)  # emulated STT latency ms
                    await self.emit("transcript_final", {
                        "speaker": speaker,
                        "speaker_name": turn.get("speaker_name", speaker),
                        "text": text,
                        "confidence": 0.99,
                        "latency_ms": latency,
                        "turn_index": idx
                    })
                    await self.engine.record_transcript(
                        self.session_id,
                        speaker=speaker,
                        text=text,
                        is_final=True,
                        confidence=0.99,
                        latency_ms=latency
                    )

                await asyncio.sleep(step_interval)

            # Turn end silence
            await self.emit("turn_status", {
                "speaker": speaker,
                "status": "SILENCE"
            })

            # Trigger automated tool execution pipeline after caller's first detailed description (Turn 0 or 2)
            if speaker == "caller" and (idx == 0 or idx == 2) and not self.pipeline_executed:
                self.pipeline_executed = True
                await self.emit("system_notification", {
                    "level": "INFO",
                    "message": "Autonomous Dispatch Triggered: Turn complete. VAD silence detected. Executing 6-tool pipeline..."
                })
                # Autonomous 6-tool pipeline
                await self.engine.run_autonomous_dispatch_pipeline(
                    session_id=self.session_id,
                    location_text=scenario["location"],
                    incident_description=scenario["description"],
                    required_unit_types=scenario.get("recommended_units", []),
                    hazards=scenario.get("hazards", [])
                )

            # Small conversational pause
            await asyncio.sleep(0.6)

        await self.emit("session_completed", {
            "session_id": self.session_id,
            "message": "Dispatch call concluded. Units in transit."
        })

    async def _on_sim_partial(self, text: str, conf: float):
        await self.emit("transcript_partial", {
            "speaker": self.active_speaker,
            "text": text,
            "confidence": conf
        })

    async def _on_sim_final(self, text: str, conf: float):
        await self.emit("transcript_final", {
            "speaker": self.active_speaker,
            "text": text,
            "confidence": conf
        })

    async def _on_sim_audio_packet(self, audio_b64: str, energy: float, speaker: str):
        await self.emit("audio_waveform", {
            "speaker": speaker,
            "energy": energy,
            "audio_b64": audio_b64
        })

    async def _on_sim_turn_change(self, speaker: str, status: str):
        await self.emit("turn_status", {
            "speaker": speaker,
            "status": status
        })

    # Live Mode Handlers (Mic from browser WebSocket)
    async def process_live_audio_chunk(self, pcm_bytes: bytes):
        """Processes incoming 16kHz PCM audio chunk from browser mic."""
        energy = calculate_pcm_energy(pcm_bytes)
        b64_audio = base64.b64encode(pcm_bytes).decode("utf-8")

        # Emit visualizer audio
        await self.emit("audio_waveform", {
            "speaker": "caller",
            "energy": energy,
            "audio_b64": b64_audio
        })

        # Voice Activity Detection (VAD)
        if energy > self.settings.vad_energy_threshold:
            self.last_audio_activity_time = time.time()
            if not self.is_caller_speaking:
                self.is_caller_speaking = True
                await self.emit("turn_status", {
                    "speaker": "caller",
                    "status": "SPEAKING"
                })

        # Forward to live AssemblyAI STT if connected
        if self.stt_client and self.stt_client.is_connected:
            await self.stt_client.send_audio(pcm_bytes)

    async def start_live_session(self):
        """Connects to live AssemblyAI Realtime WebSocket API if API key is present."""
        if self.settings.assemblyai_api_key:
            self.stt_client = AssemblyAIRealtimeClient(
                api_key=self.settings.assemblyai_api_key,
                sample_rate=self.settings.audio_sample_rate,
                on_partial=self._on_live_partial,
                on_final=self._on_live_final,
                on_session_begins=self._on_live_session_begins
            )
            connected = await self.stt_client.connect()
            if connected:
                await self.emit("system_notification", {
                    "level": "SUCCESS",
                    "message": "Connected directly to AssemblyAI Universal-3 Pro STT WebSocket."
                })
                # Start VAD background monitor
                self._vad_task = asyncio.create_task(self._live_vad_monitor())
                return

        # Fallback to simulated scenario 1
        await self.emit("system_notification", {
            "level": "WARNING",
            "message": "No ASSEMBLYAI_API_KEY detected. Running in high-fidelity simulation mode."
        })
        await self.start_scenario("scenario-1")

    async def _live_vad_monitor(self):
        """Monitors silence threshold to detect end of caller turn."""
        while self.is_active:
            await asyncio.sleep(0.1)
            if self.is_caller_speaking:
                silence_dur_ms = (time.time() - self.last_audio_activity_time) * 1000.0
                if silence_dur_ms > self.settings.vad_silence_threshold_ms:
                    self.is_caller_speaking = False
                    await self.emit("turn_status", {
                        "speaker": "caller",
                        "status": "SILENCE"
                    })
                    # End of caller turn: trigger agent processing
                    if self.current_utterance_text and not self.pipeline_executed:
                        self.pipeline_executed = True
                        await self._process_caller_turn(self.current_utterance_text)

    async def _process_caller_turn(self, caller_text: str):
        """Executes dispatch tools based on live caller speech."""
        await self.emit("system_notification", {
            "level": "INFO",
            "message": f"Turn ended. Processing caller utterance: '{caller_text[:60]}...'"
        })
        await self.engine.run_autonomous_dispatch_pipeline(
            session_id=self.session_id,
            location_text=caller_text,
            incident_description=caller_text
        )

    async def _on_live_session_begins(self, session_id: str):
        await self.emit("stt_session_begins", {"assemblyai_session_id": session_id})

    async def _on_live_partial(self, text: str, conf: float):
        self.current_utterance_text = text
        await self.emit("transcript_partial", {
            "speaker": "caller",
            "speaker_name": "Live Caller",
            "text": text,
            "confidence": conf
        })

    async def _on_live_final(self, text: str, conf: float):
        self.current_utterance_text = text
        self.accumulated_caller_text.append(text)
        await self.emit("transcript_final", {
            "speaker": "caller",
            "speaker_name": "Live Caller",
            "text": text,
            "confidence": conf
        })
        await self.engine.record_transcript(
            self.session_id,
            speaker="caller",
            text=text,
            is_final=True,
            confidence=conf
        )

    async def emit(self, event_type: str, payload: Dict[str, Any]):
        """Dispatches an event payload through the session event callback."""
        if self.on_event:
            try:
                res = self.on_event(event_type, payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Error in on_event callback: {e}")

    async def close(self):
        self.is_active = False
        if self.simulator:
            self.simulator.stop()
        if self.stt_client:
            await self.stt_client.close()
        if self._vad_task:
            self._vad_task.cancel()
