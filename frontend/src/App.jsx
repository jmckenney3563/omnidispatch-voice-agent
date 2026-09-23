import React, { useState, useEffect, useRef } from 'react';
import { 
  Radio, PhoneCall, PhoneOff, Mic, MicOff, RefreshCw, AlertTriangle, 
  ShieldAlert, Sparkles, Activity, Layers, Play, CheckCircle2
} from 'lucide-react';

import AudioVisualizer from './components/AudioVisualizer';
import TranscriptStream from './components/TranscriptStream';
import ToolInspector from './components/ToolInspector';
import FleetRadarMap from './components/FleetRadarMap';
import TicketsVault from './components/TicketsVault';
import FleetBoard from './components/FleetBoard';

export default function App() {
  const [fleet, setFleet] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState('scenario-1');
  const [toolSchemas, setToolSchemas] = useState([]);
  const [healthInfo, setHealthInfo] = useState(null);

  // Call & Audio State
  const [isCallActive, setIsCallActive] = useState(false);
  const [isLiveMic, setIsLiveMic] = useState(false);
  const [transcripts, setTranscripts] = useState([]);
  const [partialTranscript, setPartialTranscript] = useState('');
  const [activeSpeaker, setActiveSpeaker] = useState('system');
  const [turnStatus, setTurnStatus] = useState('SILENCE');
  const [audioEnergy, setAudioEnergy] = useState(0.0);
  const [toolEvents, setToolEvents] = useState([]);
  const [activeIncident, setActiveIncident] = useState(null);
  const [systemAlert, setSystemAlert] = useState(null);

  const wsRef = useRef(null);
  const micStreamRef = useRef(null);
  const audioContextRef = useRef(null);

  // Load initial data from REST endpoints
  useEffect(() => {
    fetchHealth();
    fetchFleet();
    fetchTickets();
    fetchScenarios();
    fetchTools();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      setHealthInfo(data);
    } catch (e) {
      console.error('Health fetch failed:', e);
    }
  };

  const fetchFleet = async () => {
    try {
      const res = await fetch('/api/fleet');
      const data = await res.json();
      setFleet(data);
    } catch (e) {
      console.error('Fleet fetch failed:', e);
    }
  };

  const fetchTickets = async () => {
    try {
      const res = await fetch('/api/tickets');
      const data = await res.json();
      setTickets(data);
    } catch (e) {
      console.error('Tickets fetch failed:', e);
    }
  };

  const fetchScenarios = async () => {
    try {
      const res = await fetch('/api/scenarios');
      const data = await res.json();
      setScenarios(data);
    } catch (e) {
      console.error('Scenarios fetch failed:', e);
    }
  };

  const fetchTools = async () => {
    try {
      const res = await fetch('/api/tools');
      const data = await res.json();
      setToolSchemas(data.tools || []);
    } catch (e) {
      console.error('Tools fetch failed:', e);
    }
  };

  // Connect WebSocket
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    const wsUrl = `${protocol}//${host}/ws/dispatch?scenario_id=none`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('OmniDispatch WebSocket Connected');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleWsEvent(msg);
      } catch (e) {
        console.error('Error parsing WS message:', e);
      }
    };

    ws.onclose = () => {
      console.log('OmniDispatch WebSocket Disconnected');
    };

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const handleWsEvent = (msg) => {
    const { event } = msg;

    if (event === 'session_started') {
      setIsCallActive(true);
      setTranscripts([]);
      setToolEvents([]);
      setPartialTranscript('');
      if (msg.scenario) {
        setActiveIncident({
          sector: msg.scenario.sector,
          location: msg.scenario.location,
          severity: msg.scenario.severity
        });
      }
    } else if (event === 'session_completed') {
      setIsCallActive(false);
      setTurnStatus('SILENCE');
      setPartialTranscript('');
    } else if (event === 'turn_status') {
      setTurnStatus(msg.status);
      if (msg.speaker) setActiveSpeaker(msg.speaker);
    } else if (event === 'transcript_partial') {
      setPartialTranscript(msg.text);
      if (msg.speaker) setActiveSpeaker(msg.speaker);
    } else if (event === 'transcript_final') {
      setPartialTranscript('');
      setTranscripts((prev) => [...prev, msg]);
    } else if (event === 'audio_waveform') {
      setAudioEnergy(msg.energy || 0.0);
    } else if (event === 'tool_start') {
      // Pending tool event
    } else if (event === 'tool_complete') {
      setToolEvents((prev) => [msg.execution, ...prev]);
    } else if (event === 'ticket_created') {
      const t = msg;
      setTickets((prev) => [t, ...prev]);
      if (t.location) {
        setActiveIncident({
          lat: t.location.lat,
          lng: t.location.lng,
          sector: t.location.sector,
          address: t.location.address
        });
      }
      fetchFleet();
    } else if (event === 'fleet_updated') {
      if (msg.units) setFleet(msg.units);
    } else if (event === 'system_notification') {
      setSystemAlert(msg);
      setTimeout(() => setSystemAlert(null), 5000);
    }
  };

  const startScenario = (scenarioId) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setIsLiveMic(false);
    setSelectedScenario(scenarioId);
    wsRef.current.send(JSON.stringify({
      action: 'start_scenario',
      scenario_id: scenarioId
    }));
  };

  const stopCall = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'stop_call' }));
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setIsCallActive(false);
    setIsLiveMic(false);
    setTurnStatus('SILENCE');
    setAudioEnergy(0.0);
  };

  const startLiveMic = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
      setIsLiveMic(true);
      setIsCallActive(true);
      setTranscripts([]);
      setToolEvents([]);

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(2048, 1, 1);

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        // Convert Float32 to 16-bit signed PCM
        const pcmBuffer = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcmBuffer[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(pcmBuffer.buffer);
        }
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: 'start_live_mic' }));
      }
    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Microphone access denied or unavailable. You can use the high-fidelity scenario simulator!');
    }
  };

  const resetOperationsFleet = async () => {
    stopCall();
    try {
      await fetch('/api/fleet/reset', { method: 'POST' });
      fetchFleet();
      fetchTickets();
      setActiveIncident(null);
      setTranscripts([]);
      setToolEvents([]);
    } catch (e) {
      console.error('Reset failed:', e);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans">
      {/* Top Header Navigation */}
      <header className="bg-[#0b0f19] border-b border-slate-800/90 px-6 py-3 sticky top-0 z-50 shadow-md">
        <div className="max-w-[1720px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.25)]">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-mono font-bold tracking-wider text-slate-100 uppercase">
                  OmniDispatch
                </h1>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300 font-bold uppercase tracking-widest">
                  EOC v1.0
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950/80 border border-purple-800 text-purple-300 font-semibold flex items-center gap-1">
                  <Sparkles className="w-2.5 h-2.5 text-purple-400" />
                  AssemblyAI Voice Agent
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                Universal-3 Pro Realtime STT • VAD Turn-Taking • Autonomous 6-Tool Dispatch
              </p>
            </div>
          </div>

          {/* System Status Indicators */}
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-slate-400">STT Engine:</span>
              <span className="text-slate-200 font-semibold">
                {healthInfo?.assemblyai_status || 'Universal-3 Pro'}
              </span>
            </div>

            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border font-semibold ${
              isCallActive 
                ? 'bg-amber-950/60 border-amber-600/80 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
                : 'bg-slate-900 border-slate-800 text-slate-400'
            }`}>
              <Radio className={`w-3.5 h-3.5 ${isCallActive ? 'animate-spin text-amber-400' : 'text-slate-500'}`} />
              <span>{isCallActive ? 'CALL IN PROGRESS' : 'CHANNEL IDLE'}</span>
            </div>

            <button
              onClick={resetOperationsFleet}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reset Ops</span>
            </button>
          </div>
        </div>
      </header>

      {/* Alert Banner */}
      {systemAlert && (
        <div className="bg-cyan-950/80 border-b border-cyan-800 text-cyan-200 px-6 py-1.5 text-xs font-mono flex items-center justify-center gap-2 transition-all">
          <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>{systemAlert.message}</span>
        </div>
      )}

      {/* Tactical Scenario & Call Control Bar */}
      <section className="bg-[#090d16] border-b border-slate-800 px-6 py-3">
        <div className="max-w-[1720px] mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase font-bold text-slate-400">Emergency Scenario:</span>
            <div className="flex items-center gap-2">
              {scenarios.map((scen) => (
                <button
                  key={scen.id}
                  onClick={() => setSelectedScenario(scen.id)}
                  disabled={isCallActive}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono border transition-all text-left ${
                    selectedScenario === scen.id
                      ? 'bg-cyan-950 border-cyan-500 text-cyan-200 font-bold shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                      : 'bg-slate-900/80 border-slate-800 text-slate-400 hover:border-slate-700'
                  } ${isCallActive ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <span className="block text-[10px] text-slate-500 uppercase">{scen.sector}</span>
                  <span>{scen.title}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {!isCallActive ? (
              <>
                <button
                  onClick={() => startScenario(selectedScenario)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 text-white text-xs font-mono font-bold tracking-wider shadow-[0_0_15px_rgba(239,68,68,0.4)] transition-transform active:scale-95"
                >
                  <PhoneCall className="w-4 h-4" />
                  TRIGGER EMERGENCY CALL
                </button>

                <button
                  onClick={startLiveMic}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-800/80 text-xs font-mono font-semibold transition-colors"
                >
                  <Mic className="w-4 h-4" />
                  LIVE MIC MODE
                </button>
              </>
            ) : (
              <button
                onClick={stopCall}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-700 hover:bg-red-600 text-white text-xs font-mono font-bold tracking-wider shadow-[0_0_15px_rgba(220,38,38,0.5)] animate-pulse"
              >
                <PhoneOff className="w-4 h-4" />
                TERMINATE CALL SESSION
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Main Operations Dashboard Grid */}
      <main className="flex-1 max-w-[1720px] w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Column 1: Audio Visualizer + Universal-3 Pro STT Transcript */}
        <div className="flex flex-col gap-6">
          <AudioVisualizer
            audioEnergy={audioEnergy}
            activeSpeaker={activeSpeaker}
            turnStatus={turnStatus}
            isLiveMic={isLiveMic}
            isCallActive={isCallActive}
          />
          <TranscriptStream
            transcripts={transcripts}
            partialTranscript={partialTranscript}
            activeSpeaker={activeSpeaker}
          />
        </div>

        {/* Column 2: MCP / Autonomous Tool Inspector + Tactical Radar Map */}
        <div className="flex flex-col gap-6">
          <ToolInspector
            toolEvents={toolEvents}
            schemas={toolSchemas}
          />
          <FleetRadarMap
            fleet={fleet}
            activeIncident={activeIncident}
          />
        </div>

        {/* Column 3: Active Tickets Vault + Fleet Status Board */}
        <div className="flex flex-col gap-6">
          <TicketsVault
            tickets={tickets}
          />
          <FleetBoard
            fleet={fleet}
          />
        </div>
      </main>

      {/* Tactical Footer */}
      <footer className="bg-[#090d16] border-t border-slate-800/80 px-6 py-3 text-slate-500 text-xs font-mono flex items-center justify-between">
        <div>
          OmniDispatch Voice Agent • Lablab.ai AssemblyAI Hackathon (Sept 2026) • High-Stake Autonomous Logistics
        </div>
        <div className="flex items-center gap-4 text-[11px]">
          <span>AssemblyAI Universal-3 Pro STT</span>
          <span>•</span>
          <span>Latency: &lt;180ms</span>
          <span>•</span>
          <span className="text-emerald-400">Zero-Config Operational</span>
        </div>
      </footer>
    </div>
  );
}
