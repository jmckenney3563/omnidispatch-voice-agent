import React, { useEffect, useRef } from 'react';
import { MessageSquare, Clock, CheckCircle2, User, Bot, Sparkles, Radio } from 'lucide-react';

export default function TranscriptStream({ transcripts, partialTranscript, activeSpeaker }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcripts, partialTranscript]);

  return (
    <div className="bg-[#0b0f19] border border-slate-800/80 rounded-xl p-4 flex flex-col h-[360px] shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
            Universal-3 Pro STT Transcript Stream
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Realtime Stream ({transcripts.length} turns)</span>
        </div>
      </div>

      {/* Transcript Scroll Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin">
        {transcripts.length === 0 && !partialTranscript && (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
            <Radio className="w-8 h-8 mb-2 text-slate-600 animate-pulse" />
            <p className="text-xs font-mono">Listening on WebSocket frequency...</p>
            <p className="text-[11px] text-slate-600 mt-1">Select a scenario or start live mic to begin voice dispatch dialogue.</p>
          </div>
        )}

        {transcripts.map((turn, idx) => {
          const isCaller = turn.speaker === 'caller';
          return (
            <div
              key={idx}
              className={`p-3 rounded-lg border transition-all text-xs font-sans ${
                isCaller
                  ? 'bg-amber-950/20 border-amber-900/40 text-amber-100/90 ml-2'
                  : 'bg-cyan-950/20 border-cyan-900/40 text-cyan-100/90 mr-2'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5 font-mono text-[11px]">
                <div className="flex items-center gap-1.5">
                  {isCaller ? (
                    <span className="flex items-center gap-1 text-amber-400 font-semibold px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-800/60">
                      <User className="w-3 h-3" />
                      {turn.speaker_name || 'CALLER [911-CELL]'}
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-cyan-400 font-semibold px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/60">
                      <Bot className="w-3 h-3" />
                      {turn.speaker_name || 'OMNIDISPATCH AI'}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 text-slate-400 text-[10px]">
                  {turn.latency_ms && (
                    <span className="flex items-center gap-0.5 text-cyan-400/80 bg-slate-900 px-1 py-0.5 rounded">
                      <Clock className="w-2.5 h-2.5" />
                      {turn.latency_ms}ms STT
                    </span>
                  )}
                  {turn.confidence && (
                    <span className="flex items-center gap-0.5 text-emerald-400 bg-slate-900 px-1 py-0.5 rounded">
                      <CheckCircle2 className="w-2.5 h-2.5" />
                      {Math.round(turn.confidence * 100)}%
                    </span>
                  )}
                </div>
              </div>

              <p className="leading-relaxed whitespace-pre-wrap font-mono text-[12.5px] mt-1 text-slate-200">
                {turn.text}
              </p>
            </div>
          );
        })}

        {/* Live Partial Transcript Streaming Bubble */}
        {partialTranscript && (
          <div className="p-3 rounded-lg border border-cyan-700/50 bg-cyan-950/30 text-cyan-200 text-xs font-mono animate-pulse mr-2">
            <div className="flex items-center gap-1.5 text-[11px] text-cyan-400 mb-1">
              <Sparkles className="w-3 h-3 animate-spin" />
              <span className="uppercase font-semibold">
                Universal-3 Pro Streaming ({activeSpeaker === 'caller' ? 'CALLER' : 'AGENT'})
              </span>
            </div>
            <p className="italic text-slate-300">
              {partialTranscript}
              <span className="inline-block w-1.5 h-3.5 bg-cyan-400 ml-1 translate-y-0.5 animate-bounce" />
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
