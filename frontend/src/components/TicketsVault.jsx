import React from 'react';
import { Ticket, AlertCircle, Clock, MapPin, Truck, CheckCircle2 } from 'lucide-react';

export default function TicketsVault({ tickets }) {
  const getSeverityStyle = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-950/80 border-red-700 text-red-300 animate-pulse';
      case 'HIGH':
        return 'bg-amber-950/80 border-amber-700 text-amber-300';
      case 'MEDIUM':
        return 'bg-yellow-950/80 border-yellow-700 text-yellow-300';
      default:
        return 'bg-slate-900 border-slate-800 text-slate-300';
    }
  };

  return (
    <div className="bg-[#0b0f19] border border-slate-800/80 rounded-xl p-4 flex flex-col h-[420px] shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <Ticket className="w-4 h-4 text-amber-400" />
          <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
            Active Dispatch Tickets Vault
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          {tickets.length} Registered Incidents
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 scrollbar-thin">
        {tickets.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
            <CheckCircle2 className="w-8 h-8 mb-2 text-slate-600" />
            <p className="text-xs font-mono">No Active Emergency Tickets</p>
            <p className="text-[11px] text-slate-600 mt-1">Autonomous tickets will generate automatically during call flow.</p>
          </div>
        ) : (
          tickets.map((ticket, idx) => (
            <div
              key={ticket.id || idx}
              className="border border-slate-800/90 rounded-lg p-3 bg-slate-900/40 hover:bg-slate-900/70 transition-colors text-xs font-mono space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-cyan-400 text-[13px]">
                  #{ticket.id}
                </span>
                <span className={`px-2 py-0.5 rounded border text-[10px] font-bold uppercase ${getSeverityStyle(ticket.severity)}`}>
                  {ticket.severity}
                </span>
              </div>

              <div className="text-slate-200 font-sans text-[12px] font-medium">
                {ticket.incident_type}
              </div>

              <div className="flex items-start gap-1.5 text-slate-400 text-[11px]">
                <MapPin className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                <span className="truncate">{ticket.location?.address || 'Target Coordinates'}</span>
              </div>

              <div className="flex items-center gap-2 pt-1 border-t border-slate-800/60 text-[11px]">
                <Truck className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-slate-400">Units:</span>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {(ticket.assigned_units || []).map((uid) => (
                    <span
                      key={uid}
                      className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 text-[10px] border border-slate-700 font-semibold"
                    >
                      {uid}
                    </span>
                  ))}
                </div>
              </div>

              <p className="text-[11px] text-slate-400 font-sans italic line-clamp-2 pt-1">
                "{ticket.description}"
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
