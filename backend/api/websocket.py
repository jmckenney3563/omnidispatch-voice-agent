"""
Bi-directional WebSocket Manager for Voice Agent Audio, Transcripts, and Tool Events.
Endpoint: /ws/dispatch
"""
import json
import base64
import asyncio
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect

from backend.dispatch.engine import get_dispatch_engine
from backend.assemblyai.voice_agent import VoiceAgentSession

logger = logging.getLogger("omnidispatch.websocket")


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.active_sessions: Dict[str, VoiceAgentSession] = {}
        self.engine = get_dispatch_engine()
        # Wire up engine events to broadcast
        self.engine.subscribe(self._on_engine_event)

    async def _on_engine_event(self, event_type: str, payload: Dict):
        # Broadcast to matching session or all active connections
        session_id = payload.get("session_id")
        if session_id and session_id in self.active_connections:
            ws = self.active_connections[session_id]
            try:
                await ws.send_text(json.dumps({"event": event_type, **payload}))
            except Exception:
                pass
        else:
            # Broadcast to all
            await self.broadcast({"event": event_type, **payload})

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket client connected: session_id={session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.active_sessions:
            # Clean up session
            asyncio.create_task(self.active_sessions[session_id].close())
            del self.active_sessions[session_id]
        logger.info(f"WebSocket client disconnected: session_id={session_id}")

    async def send_to_session(self, session_id: str, message: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass

    async def broadcast(self, message: dict):
        text = json.dumps(message)
        for ws in list(self.active_connections.values()):
            try:
                await ws.send_text(text)
            except Exception:
                pass


ws_manager = WebSocketConnectionManager()


async def handle_dispatch_websocket(
    websocket: WebSocket,
    session_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    live_mode: bool = False
):
    import uuid
    sid = session_id or f"sess-{uuid.uuid4().hex[:8]}"
    await ws_manager.connect(websocket, sid)

    async def session_event_emitter(event_type: str, payload: dict):
        await ws_manager.send_to_session(sid, {"event": event_type, "session_id": sid, **payload})

    voice_session = VoiceAgentSession(
        session_id=sid,
        on_event=session_event_emitter,
        live_mode=live_mode
    )
    ws_manager.active_sessions[sid] = voice_session

    # Send initial welcome & system info
    await voice_session.emit("system_notification", {
        "level": "INFO",
        "message": f"OmniDispatch Voice Session Initialized ({sid}). AssemblyAI Universal-3 Pro Ready."
    })

    # If scenario_id provided on connect and not live_mode, auto-trigger scenario
    if scenario_id and scenario_id.lower() not in ("none", "", "null", "false") and not live_mode:
        asyncio.create_task(voice_session.start_scenario(scenario_id))

    try:
        while True:
            # Can receive text JSON control messages or raw binary audio
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                # Incoming 16kHz PCM audio chunk from browser mic
                await voice_session.process_live_audio_chunk(message["bytes"])
            elif "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                    action = data.get("action")

                    if action == "start_scenario":
                        scen_id = data.get("scenario_id", "scenario-1")
                        asyncio.create_task(voice_session.start_scenario(scen_id))
                    elif action == "start_live_mic":
                        voice_session.live_mode = True
                        asyncio.create_task(voice_session.start_live_session())
                    elif action == "stop_call":
                        await voice_session.close()
                        await voice_session.emit("system_notification", {
                            "level": "INFO",
                            "message": "Call stopped by operator."
                        })
                    elif action == "ping":
                        await ws_manager.send_to_session(sid, {"event": "pong"})
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        logger.info(f"Client disconnected gracefully: {sid}")
    except Exception as e:
        logger.error(f"WebSocket error in session {sid}: {e}")
    finally:
        ws_manager.disconnect(sid)
