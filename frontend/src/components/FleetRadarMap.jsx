import React, { useState } from 'react';
import { Compass, Navigation, Shield, Flame, Truck, AlertTriangle, Radio } from 'lucide-react';

export default function FleetRadarMap({ fleet, activeIncident }) {
  const [selectedUnit, setSelectedUnit] = useState(null);

  // Map coordinate conversion: Center on Metro (40.75, -73.97)
  const CENTER_LAT = 40.755;
  const CENTER_LNG = -73.965;
  const LAT_SPAN = 0.16;
  const LNG_SPAN = 0.20;

  const getCanvasCoords = (lat, lng) => {
    // Return x, y in SVG percentage (0 - 100)
    const x = ((lng - (CENTER_LNG - LNG_SPAN / 2)) / LNG_SPAN) * 100;
    // Invert Y so north is up
    const y = 100 - ((lat - (CENTER_LAT - LAT_SPAN / 2)) / LAT_SPAN) * 100;
    return {
      x: Math.max(5, Math.min(95, x)),
      y: Math.max(5, Math.min(95, y))
    };
  };

  const incidentCoords = activeIncident?.lat && activeIncident?.lng
    ? getCanvasCoords(activeIncident.lat, activeIncident.lng)
    : null;

  return (
    <div className="bg-[#0b0f19] border border-slate-800/80 rounded-xl p-4 flex flex-col h-[420px] shadow-lg relative">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-2">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-emerald-400" />
          <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
            Tactical Sector Radar & Fleet Positioning
          </h3>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Avail ({fleet.filter(u => u.status === 'AVAILABLE').length})
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" /> En Route ({fleet.filter(u => u.status === 'EN_ROUTE' || u.status === 'DISPATCHED').length})
          </span>
          {activeIncident && (
            <span className="flex items-center gap-1 text-crimson-400 text-red-400 font-semibold animate-pulse">
              <AlertTriangle className="w-3.5 h-3.5" /> INCIDENT ACTIVE
            </span>
          )}
        </div>
      </div>

      {/* Radar Map SVG Display */}
      <div className="relative flex-1 w-full bg-[#06080e] rounded-lg overflow-hidden border border-slate-900 radar-grid flex items-center justify-center">
        <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          {/* Concentric Radar Rings */}
          <circle cx="50" cy="50" r="45" fill="none" stroke="#1e293b" strokeWidth="0.4" strokeDasharray="1,1" />
          <circle cx="50" cy="50" r="30" fill="none" stroke="#1e293b" strokeWidth="0.4" strokeDasharray="1,1" />
          <circle cx="50" cy="50" r="15" fill="none" stroke="#1e293b" strokeWidth="0.4" strokeDasharray="1,1" />

          {/* Crosshair Axes */}
          <line x1="50" y1="0" x2="50" y2="100" stroke="#1e293b" strokeWidth="0.4" />
          <line x1="0" y1="50" x2="100" y2="50" stroke="#1e293b" strokeWidth="0.4" />

          {/* Sector Labels */}
          <text x="52" y="8" fill="#475569" fontSize="2.2" fontFamily="monospace">SECTOR NORTH (I-95)</text>
          <text x="52" y="96" fill="#475569" fontSize="2.2" fontFamily="monospace">SECTOR SOUTH (CORRIDOR)</text>
          <text x="4" y="48" fill="#475569" fontSize="2.2" fontFamily="monospace">SECTOR WEST (PORT)</text>
          <text x="76" y="48" fill="#475569" fontSize="2.2" fontFamily="monospace">TRANSIT HUB</text>

          {/* Route Vectors from En-Route Units to Incident */}
          {incidentCoords && fleet.map((unit) => {
            if (unit.status === 'EN_ROUTE' || unit.status === 'DISPATCHED') {
              const uCoord = getCanvasCoords(unit.coordinates.lat, unit.coordinates.lng);
              return (
                <g key={`vector-${unit.id}`}>
                  <line
                    x1={uCoord.x}
                    y1={uCoord.y}
                    x2={incidentCoords.x}
                    y2={incidentCoords.y}
                    stroke="#f59e0b"
                    strokeWidth="0.6"
                    strokeDasharray="1.5,1.5"
                    opacity="0.8"
                  />
                </g>
              );
            }
            return null;
          })}

          {/* Incident Distress Marker */}
          {incidentCoords && (
            <g transform={`translate(${incidentCoords.x}, ${incidentCoords.y})`}>
              <circle r="4.5" fill="none" stroke="#ef4444" strokeWidth="0.6" className="animate-ping" />
              <circle r="2" fill="#ef4444" />
              <text x="3" y="-2" fill="#f87171" fontSize="2.8" fontWeight="bold" fontFamily="monospace">
                TARGET: {activeIncident.sector || 'INCIDENT'}
              </text>
            </g>
          )}

          {/* Fleet Unit Markers */}
          {fleet.map((unit) => {
            const coord = getCanvasCoords(unit.coordinates.lat, unit.coordinates.lng);
            const isEnRoute = unit.status === 'EN_ROUTE' || unit.status === 'DISPATCHED';
            const isSelected = selectedUnit?.id === unit.id;

            let fillColor = '#10b981'; // green available
            if (isEnRoute) fillColor = '#f59e0b'; // amber en route
            if (unit.status === 'OFFLINE') fillColor = '#64748b';

            return (
              <g
                key={unit.id}
                className="cursor-pointer transition-transform hover:scale-125"
                onClick={() => setSelectedUnit(unit)}
              >
                {isEnRoute && (
                  <circle
                    cx={coord.x}
                    cy={coord.y}
                    r="3.2"
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="0.5"
                    className="animate-ping"
                  />
                )}
                <circle
                  cx={coord.x}
                  cy={coord.y}
                  r={isSelected ? "2.2" : "1.6"}
                  fill={fillColor}
                  stroke={isSelected ? "#ffffff" : "#000000"}
                  strokeWidth="0.4"
                />
                <text
                  x={coord.x + 2.2}
                  y={coord.y + 1}
                  fill={isEnRoute ? '#fbbf24' : '#94a3b8'}
                  fontSize="2.1"
                  fontFamily="monospace"
                  fontWeight={isEnRoute ? 'bold' : 'normal'}
                >
                  {unit.callsign}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Selected Unit Telemetry Overlay Card */}
        {selectedUnit && (
          <div className="absolute bottom-3 left-3 bg-[#0b0f19]/95 backdrop-blur-md border border-slate-700 p-3 rounded-lg text-xs font-mono max-w-xs shadow-2xl">
            <div className="flex items-center justify-between pb-1 border-b border-slate-800 mb-1.5">
              <span className="font-bold text-cyan-300">{selectedUnit.callsign}</span>
              <button
                onClick={() => setSelectedUnit(null)}
                className="text-slate-400 hover:text-white text-xs px-1"
              >
                ✕
              </button>
            </div>
            <div className="space-y-1 text-[11px] text-slate-300">
              <div><span className="text-slate-500">TYPE:</span> {selectedUnit.type}</div>
              <div>
                <span className="text-slate-500">STATUS:</span>{' '}
                <span className={selectedUnit.status === 'AVAILABLE' ? 'text-emerald-400' : 'text-amber-400'}>
                  {selectedUnit.status}
                </span>
                {selectedUnit.eta_minutes && ` (ETA: ${selectedUnit.eta_minutes}m)`}
              </div>
              <div><span className="text-slate-500">SECTOR:</span> {selectedUnit.coordinates.sector}</div>
              <div><span className="text-slate-500">FREQ:</span> {selectedUnit.contact_freq}</div>
              <div><span className="text-slate-500">CREW:</span> {selectedUnit.crew_count} Operators</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
