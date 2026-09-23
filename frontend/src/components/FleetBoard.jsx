import React from 'react';
import { Shield, Radio, Navigation, Clock } from 'lucide-react';

export default function FleetBoard({ fleet }) {
  return (
    <div className="bg-[#0b0f19] border border-slate-800/80 rounded-xl p-4 shadow-lg flex flex-col">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
            Operational Fleet Status Roster ({fleet.length} Units)
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          Radio Net: All Units Synchronized
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-slate-800/80 text-slate-400 text-[11px]">
              <th className="pb-2 font-semibold">CALLSIGN</th>
              <th className="pb-2 font-semibold">CLASS / TYPE</th>
              <th className="pb-2 font-semibold">STATION / SECTOR</th>
              <th className="pb-2 font-semibold">STATUS</th>
              <th className="pb-2 font-semibold">RESPONSE ETA</th>
              <th className="pb-2 font-semibold">COMMS FREQ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {fleet.map((unit) => {
              const isEnRoute = unit.status === 'EN_ROUTE' || unit.status === 'DISPATCHED';
              return (
                <tr key={unit.id} className="hover:bg-slate-900/40 transition-colors">
                  <td className="py-2.5 font-bold text-slate-200">
                    {unit.callsign}
                  </td>
                  <td className="py-2.5 text-slate-400 text-[11px]">
                    {unit.type.replace(/_/g, ' ')}
                  </td>
                  <td className="py-2.5 text-slate-300">
                    {unit.coordinates.sector}
                  </td>
                  <td className="py-2.5">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold border ${
                      isEnRoute
                        ? 'bg-amber-950/80 text-amber-300 border-amber-700 animate-pulse'
                        : unit.status === 'AVAILABLE'
                        ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                        : 'bg-slate-900 text-slate-400 border-slate-800'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${isEnRoute ? 'bg-amber-400' : 'bg-emerald-400'}`} />
                      {unit.status}
                    </span>
                  </td>
                  <td className="py-2.5 text-cyan-400">
                    {unit.eta_minutes ? (
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-cyan-500" />
                        {unit.eta_minutes} min
                      </span>
                    ) : (
                      <span className="text-slate-500">STBY</span>
                    )}
                  </td>
                  <td className="py-2.5 text-slate-400 text-[11px]">
                    {unit.contact_freq}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
