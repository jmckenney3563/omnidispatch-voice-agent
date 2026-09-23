import React, { useEffect, useRef } from 'react';
import { Mic, Activity, Volume2, Radio } from 'lucide-react';

export default function AudioVisualizer({ audioEnergy, activeSpeaker, turnStatus, isLiveMic, isCallActive }) {
  const canvasRef = useRef(null);
  const phaseRef = useRef(0);
  const energyRef = useRef(audioEnergy);

  useEffect(() => {
    energyRef.current = audioEnergy;
  }, [audioEnergy]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    const render = () => {
      phaseRef.current += 0.08;
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      // Background subtle grid line
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();

      const currentEnergy = Math.max(0.04, energyRef.current || 0);
      const isSpeaking = turnStatus === 'SPEAKING' && isCallActive;

      // Color based on speaker
      let strokeColor = '#38bdf8'; // Cyan for agent
      if (activeSpeaker === 'caller') {
        strokeColor = '#f59e0b'; // Amber for caller
      } else if (!isSpeaking) {
        strokeColor = '#475569'; // Slate for idle/silence
      }

      // Draw primary waveform
      ctx.lineWidth = isSpeaking ? 2.5 : 1.2;
      ctx.strokeStyle = strokeColor;
      ctx.beginPath();

      const numPoints = 80;
      const step = width / numPoints;

      for (let i = 0; i <= numPoints; i++) {
        const x = i * step;
        const normalizedX = (i / numPoints) * Math.PI * 4;
        const amp = isSpeaking ? (currentEnergy * height * 0.42) : 2.0;

        // Harmonic superposition for realistic voice waveform
        const y = height / 2 +
          Math.sin(normalizedX + phaseRef.current) * amp * 0.7 +
          Math.sin(normalizedX * 2.3 - phaseRef.current * 1.4) * amp * 0.3;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      // Second harmonic ghost trace for depth
      if (isSpeaking) {
        ctx.lineWidth = 1;
        ctx.strokeStyle = strokeColor + '44';
        ctx.beginPath();
        for (let i = 0; i <= numPoints; i++) {
          const x = i * step;
          const normalizedX = (i / numPoints) * Math.PI * 4;
          const amp = currentEnergy * height * 0.28;
          const y = height / 2 + Math.sin(normalizedX * 1.5 + phaseRef.current * 0.8) * amp;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [turnStatus, activeSpeaker, isCallActive]);

  const dbLevel = Math.round((energyRef.current || 0) * 60);

  return (
    <div className="bg-[#0b0f19] border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono tracking-wider font-semibold text-slate-300 uppercase">
            Acoustic Telemetry & VAD
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isLiveMic ? (
            <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-red-950/80 border border-red-800 text-red-400 animate-pulse">
              <Mic className="w-3 h-3" /> LIVE MIC
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800 text-cyan-400">
              <Radio className="w-3 h-3" /> SYNTHESIZED PCM 16kHz
            </span>
          )}
          <span className="text-[11px] font-mono text-slate-400">
            {dbLevel > 0 ? `-${60 - dbLevel} dB` : '-INF'}
          </span>
        </div>
      </div>

      {/* Waveform Canvas */}
      <div className="relative w-full h-24 bg-[#070a10] rounded-lg overflow-hidden border border-slate-900 flex items-center justify-center">
        <canvas
          ref={canvasRef}
          width={500}
          height={96}
          className="w-full h-full object-cover"
        />
        {!isCallActive && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[1px]">
            <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">
              Audio Channel Standby
            </span>
          </div>
        )}
      </div>

      {/* Speaker & VAD Indicators */}
      <div className="grid grid-cols-3 gap-2 mt-3 pt-2 border-t border-slate-800/60 text-xs font-mono">
        <div className={`flex items-center justify-between p-2 rounded border ${
          activeSpeaker === 'caller' && turnStatus === 'SPEAKING'
            ? 'bg-amber-950/40 border-amber-500/80 text-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.2)]'
            : 'bg-slate-900/40 border-slate-800 text-slate-400'
        }`}>
          <span>CALLER [911]</span>
          <span className={`w-2 h-2 rounded-full ${
            activeSpeaker === 'caller' && turnStatus === 'SPEAKING'
              ? 'bg-amber-400 animate-ping'
              : 'bg-slate-700'
          }`} />
        </div>

        <div className={`flex items-center justify-between p-2 rounded border ${
          activeSpeaker === 'agent' && turnStatus === 'SPEAKING'
            ? 'bg-cyan-950/40 border-cyan-500/80 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
            : 'bg-slate-900/40 border-slate-800 text-slate-400'
        }`}>
          <span>OMNIDISPATCH AI</span>
          <span className={`w-2 h-2 rounded-full ${
            activeSpeaker === 'agent' && turnStatus === 'SPEAKING'
              ? 'bg-cyan-400 animate-ping'
              : 'bg-slate-700'
          }`} />
        </div>

        <div className={`flex items-center justify-between p-2 rounded border ${
          turnStatus === 'SILENCE' || !isCallActive
            ? 'bg-slate-800/40 border-slate-700 text-slate-300'
            : 'bg-slate-900/40 border-slate-800 text-slate-500'
        }`}>
          <span>VAD SILENCE</span>
          <span className={`w-2 h-2 rounded-full ${
            turnStatus === 'SILENCE' && isCallActive ? 'bg-emerald-400' : 'bg-slate-700'
          }`} />
        </div>
      </div>
    </div>
  );
}
