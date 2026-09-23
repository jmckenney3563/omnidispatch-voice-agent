import React, { useState } from 'react';
import { Cpu, Terminal, ChevronDown, ChevronRight, CheckCircle, Code2, Play } from 'lucide-react';

export default function ToolInspector({ toolEvents, schemas }) {
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [activeTab, setActiveTab] = useState('events'); // 'events' | 'schemas'

  const toggleExpand = (idx) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  return (
    <div className="bg-[#0b0f19] border border-slate-800/80 rounded-xl p-4 flex flex-col h-[360px] shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
            MCP & Autonomous Tool Execution
          </h3>
        </div>

        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-[11px] font-mono">
          <button
            onClick={() => setActiveTab('events')}
            className={`px-2 py-1 rounded transition-colors ${
              activeTab === 'events'
                ? 'bg-purple-950 text-purple-300 border border-purple-800/80 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Live Pipeline ({toolEvents.length})
          </button>
          <button
            onClick={() => setActiveTab('schemas')}
            className={`px-2 py-1 rounded transition-colors ${
              activeTab === 'schemas'
                ? 'bg-purple-950 text-purple-300 border border-purple-800/80 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            6 Tool Schemas
          </button>
        </div>
      </div>

      {activeTab === 'events' ? (
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 scrollbar-thin">
          {toolEvents.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
              <Terminal className="w-8 h-8 mb-2 text-slate-600" />
              <p className="text-xs font-mono">Autonomous Dispatch Pipeline Idle</p>
              <p className="text-[11px] text-slate-600 mt-1">Tools automatically execute upon caller turn completion.</p>
            </div>
          ) : (
            toolEvents.map((evt, idx) => {
              const exec = evt.execution || evt;
              const isExpanded = expandedIndex === idx;
              return (
                <div
                  key={idx}
                  className="border border-slate-800 rounded-lg bg-slate-900/50 overflow-hidden text-xs font-mono transition-colors"
                >
                  <button
                    onClick={() => toggleExpand(idx)}
                    className="w-full flex items-center justify-between p-2.5 hover:bg-slate-800/40 text-left transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-400">
                        <CheckCircle className="w-3.5 h-3.5" />
                      </span>
                      <span className="font-semibold text-purple-300">
                        {exec.tool_name || 'unknown_tool'}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-slate-400">
                      {exec.duration_ms && (
                        <span className="text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/60">
                          {exec.duration_ms}ms
                        </span>
                      )}
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-400" />
                      )}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="p-3 bg-[#070a12] border-t border-slate-800/80 space-y-2 text-[11px]">
                      <div>
                        <span className="text-slate-400 font-semibold uppercase text-[10px]">Parameters:</span>
                        <pre className="mt-1 p-2 rounded bg-slate-950 border border-slate-800/60 text-slate-300 overflow-x-auto text-[10.5px]">
                          {JSON.stringify(exec.arguments || {}, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <span className="text-emerald-400 font-semibold uppercase text-[10px]">Output Result:</span>
                        <pre className="mt-1 p-2 rounded bg-slate-950 border border-emerald-950 text-emerald-300/90 overflow-x-auto text-[10.5px]">
                          {JSON.stringify(exec.result || {}, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 scrollbar-thin">
          {(schemas || []).map((toolDef, idx) => {
            const fn = toolDef.function || {};
            return (
              <div key={idx} className="border border-slate-800 rounded-lg p-2.5 bg-slate-900/40 text-xs font-mono">
                <div className="flex items-center justify-between text-purple-300 font-semibold mb-1">
                  <span className="flex items-center gap-1.5">
                    <Code2 className="w-3.5 h-3.5 text-cyan-400" />
                    {fn.name}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                    JSON Schema
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 font-sans mb-2 leading-relaxed">
                  {fn.description}
                </p>
                <div className="text-[10.5px] bg-slate-950 p-2 rounded border border-slate-800/60 text-slate-400">
                  <span className="text-slate-500 font-bold uppercase text-[9px]">Properties: </span>
                  {Object.keys(fn.parameters?.properties || {}).join(', ')}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
