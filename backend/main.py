"""
OmniDispatch Voice Agent - Main FastAPI Application.
Autonomous Emergency & Fleet Logistics Voice Agent.
"""
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import get_settings
from backend.api.routes import router as api_router
from backend.api.websocket import handle_dispatch_websocket

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Autonomous Emergency & Fleet Logistics Voice Agent built for the AssemblyAI Voice Agent Hackathon."
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API
app.include_router(api_router)


# WebSocket Route
@app.websocket("/ws/dispatch")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Query(None),
    scenario_id: str = Query(None),
    live_mode: bool = Query(False)
):
    await handle_dispatch_websocket(
        websocket=websocket,
        session_id=session_id,
        scenario_id=scenario_id,
        live_mode=live_mode
    )


# Frontend static files mounting
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def root_fallback():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api_health": "/api/health",
            "frontend_status": "Building or running via Vite dev server on port 5173"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main.py:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
