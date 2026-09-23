"""
AssemblyAI Realtime STT WebSocket Client & High-Fidelity Audio Simulator.
Supports Universal-3 Pro STT streaming via live WebSocket or zero-config simulation.
"""
import math
import json
import base64
import asyncio
import struct
import logging
from typing import Optional, Callable, Dict, Any, List
import websockets
from backend.config import get_settings
from backend.assemblyai.scenarios import (
    generate_pcm_audio_chunk,
    get_scenario_by_id,
    SCENARIOS
)

logger = logging.getLogger("omnidispatch.assemblyai")


def calculate_pcm_energy(pcm_bytes: bytes) -> float:
    """Calculates normalized RMS energy level from 16-bit PCM bytes."""
    if not pcm_bytes or len(pcm_bytes) < 2:
        return 0.0
    count = len(pcm_bytes) // 2
    shorts = struct.unpack(f"<{count}h", pcm_bytes[:count * 2])
    sum_squares = sum(s * s for s in shorts)
    rms = math.sqrt(sum_squares / count)
    return min(1.0, rms / 32768.0)


class AssemblyAIRealtimeClient:
    """
    Live AssemblyAI Realtime WebSocket Client.
    Connects to wss://api.assemblyai.com/v2/realtime/ws.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        sample_rate: int = 16000,
        on_partial: Optional[Callable[[str, float], Any]] = None,
        on_final: Optional[Callable[[str, float], Any]] = None,
        on_session_begins: Optional[Callable[[str], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None
    ):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.assemblyai_api_key
        self.sample_rate = sample_rate or self.settings.audio_sample_rate
        self.on_partial = on_partial
        self.on_final = on_final
        self.on_session_begins = on_session_begins
        self.on_error = on_error
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        if not self.api_key:
            logger.warning("No AssemblyAI API key configured. Client cannot connect to live API.")
            return False

        url = f"{self.settings.assemblyai_realtime_url}?sample_rate={self.sample_rate}"
        headers = {"Authorization": self.api_key}

        try:
            self.ws = await websockets.connect(url, extra_headers=headers)
            self.is_connected = True
            self._receive_task = asyncio.create_task(self._listen_loop())
            logger.info("Connected to AssemblyAI Realtime WebSocket API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to AssemblyAI WebSocket: {e}")
            if self.on_error:
                self.on_error(str(e))
            self.is_connected = False
            return False

    async def send_audio(self, pcm_bytes: bytes):
        """Sends raw 16-bit PCM audio buffer to AssemblyAI."""
        if not self.is_connected or not self.ws:
            return
        try:
            # AssemblyAI accepts raw binary audio or base64 JSON
            payload = json.dumps({"audio_data": base64.b64encode(pcm_bytes).decode("utf-8")})
            await self.ws.send(payload)
        except Exception as e:
            logger.error(f"Error sending audio to AssemblyAI: {e}")

    async def _listen_loop(self):
        try:
            async for raw_msg in self.ws:
                msg = json.loads(raw_msg)
                msg_type = msg.get("message_type")

                if msg_type == "SessionBegins":
                    session_id = msg.get("session_id", "unknown")
                    if self.on_session_begins:
                        res = self.on_session_begins(session_id)
                        if asyncio.iscoroutine(res):
                            await res
                elif msg_type == "PartialTranscript":
                    text = msg.get("text", "")
                    if text and self.on_partial:
                        res = self.on_partial(text, msg.get("confidence", 0.9))
                        if asyncio.iscoroutine(res):
                            await res
                elif msg_type == "FinalTranscript":
                    text = msg.get("text", "")
                    if text and self.on_final:
                        res = self.on_final(text, msg.get("confidence", 0.98))
                        if asyncio.iscoroutine(res):
                            await res
                elif msg_type == "SessionTerminated":
                    break
        except Exception as e:
            logger.error(f"AssemblyAI receive loop exception: {e}")
            if self.on_error:
                self.on_error(str(e))
        finally:
            self.is_connected = False

    async def close(self):
        self.is_connected = False
        if self.ws:
            try:
                # Send terminate session message
                await self.ws.send(json.dumps({"terminate_session": True}))
                await self.ws.close()
            except Exception:
                pass
        if self._receive_task:
            self._receive_task.cancel()


class AssemblyAISimulator:
    """
    High-fidelity Voice & STT Simulator for zero-config out-of-the-box operation.
    Emulates AssemblyAI Universal-3 Pro STT streaming, VAD turn transitions,
    and synthesized audio waveform energy.
    """

    def __init__(
        self,
        on_partial: Optional[Callable[[str, float], Any]] = None,
        on_final: Optional[Callable[[str, float], Any]] = None,
        on_audio_packet: Optional[Callable[[str, float, str], Any]] = None,
        on_turn_change: Optional[Callable[[str, str], Any]] = None,
        speed_multiplier: float = 1.0
    ):
        self.on_partial = on_partial
        self.on_final = on_final
        self.on_audio_packet = on_audio_packet
        self.on_turn_change = on_turn_change
        self.speed_multiplier = max(0.2, min(5.0, speed_multiplier))
        self.is_running = False
        self._current_task: Optional[asyncio.Task] = None

    async def run_scenario(self, scenario_id: str):
        """Simulates full scenario audio + STT transcription in real time."""
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            scenario = SCENARIOS[0]

        self.is_running = True
        logger.info(f"Starting scenario simulation: {scenario['title']}")

        for turn in scenario["turns"]:
            if not self.is_running:
                break

            speaker = turn["speaker"]
            text = turn["text"]
            duration_s = (turn["duration_ms"] / 1000.0) / self.speed_multiplier
            freq = turn.get("frequency", 220.0)
            amp = turn.get("amplitude", 0.5)

            # Signal turn start
            if self.on_turn_change:
                res = self.on_turn_change(speaker, "SPEAKING")
                if asyncio.iscoroutine(res):
                    await res

            # Break turn text into progressive words to simulate Universal-3 Pro real-time stream
            words = text.split(" ")
            num_chunks = max(4, min(len(words), 12))
            chunk_time = duration_s / num_chunks

            accumulated_words = []
            for i in range(num_chunks):
                if not self.is_running:
                    break

                # Slice words for partial transcript
                end_idx = int(((i + 1) / num_chunks) * len(words))
                current_text = " ".join(words[:end_idx])

                # Generate a short PCM audio slice
                pcm = generate_pcm_audio_chunk(
                    frequency_hz=freq + (i * 3.0),
                    duration_seconds=min(0.2, chunk_time),
                    amplitude=amp
                )
                energy = calculate_pcm_energy(pcm)
                b64_audio = base64.b64encode(pcm).decode("utf-8")

                # Send audio packet
                if self.on_audio_packet:
                    res = self.on_audio_packet(b64_audio, energy, speaker)
                    if asyncio.iscoroutine(res):
                        await res

                # Send partial transcript if caller is speaking
                if i < num_chunks - 1:
                    if self.on_partial:
                        res = self.on_partial(current_text, 0.92)
                        if asyncio.iscoroutine(res):
                            await res
                else:
                    # Final chunk: send final transcript
                    if self.on_final:
                        res = self.on_final(text, 0.99)
                        if asyncio.iscoroutine(res):
                            await res

                await asyncio.sleep(chunk_time)

            # Signal turn end / silence VAD
            if self.on_turn_change:
                res = self.on_turn_change(speaker, "SILENCE")
                if asyncio.iscoroutine(res):
                    await res

            # Small silence pause between turns
            pause_time = (0.7 / self.speed_multiplier)
            await asyncio.sleep(pause_time)

        self.is_running = False
        logger.info(f"Finished scenario simulation: {scenario['title']}")

    def stop(self):
        self.is_running = False
        if self._current_task:
            self._current_task.cancel()
