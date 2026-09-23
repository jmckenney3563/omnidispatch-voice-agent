"""
Configuration management for OmniDispatch Voice Agent.
Supports environment variables from .env and sensible defaults.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Service Information
    app_name: str = "OmniDispatch - Autonomous Emergency & Fleet Logistics Voice Agent"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # AssemblyAI Configuration
    assemblyai_api_key: Optional[str] = None
    assemblyai_realtime_url: str = "wss://api.assemblyai.com/v2/realtime/ws"
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_chunk_ms: int = 100

    # Turn-Taking and VAD
    vad_silence_threshold_ms: int = 750
    vad_energy_threshold: float = 0.015
    auto_tool_execution: bool = True

    # Simulation Defaults
    enable_simulation_fallback: bool = True
    simulation_speed_multiplier: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()


def get_settings() -> Settings:
    return settings
