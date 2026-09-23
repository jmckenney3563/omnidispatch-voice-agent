"""
AssemblyAI Realtime Integration Package for OmniDispatch.
"""
from backend.assemblyai.client import AssemblyAIRealtimeClient, AssemblyAISimulator
from backend.assemblyai.voice_agent import VoiceAgentSession
from backend.assemblyai.scenarios import SCENARIOS, get_all_scenarios, get_scenario_by_id

__all__ = [
    "AssemblyAIRealtimeClient",
    "AssemblyAISimulator",
    "VoiceAgentSession",
    "SCENARIOS",
    "get_all_scenarios",
    "get_scenario_by_id",
]
