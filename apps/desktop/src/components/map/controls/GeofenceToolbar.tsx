import { useState } from 'react';
import { useMapStore } from '@/stores/useMapStore';
import type { Geofence } from '../layers/GeofenceLayer';

export function GeofenceToolbar() {
  const {
    geofenceEditMode, setGeofenceEditMode, geofences,
    addGeofence, removeGeofence, geofenceVertices,
    removeLastVertex, clearGeofenceVertices,
  } = useMapStore();
  const [name, setName] = useState('');
  const [alertType, setAlertType] = useState<'entry' | 'exit' | 'both'>('both');

  const handleSave = () => {
    if (!name.trim() || geofenceVertices.length < 3) return;
    // Close the polygon by repeating the first vertex
    const ring = [...geofenceVertices, geofenceVertices[0]];
    const geofence: Geofence = {
      id: `gf-${Date.now()}`,
      name: name.trim(),
      polygon: {
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [ring] },
        properties: {},
      },
      alertType,
    };
    addGeofence(geofence);
    setName('');
    clearGeofenceVertices();
    setGeofenceEditMode(false);
  };

  const handleCancel = () => {
    clearGeofenceVertices();
    setName('');
    setGeofenceEditMode(false);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => {
          if (geofenceEditMode) {
            handleCancel();
          } else {
            clearGeofenceVertices();
            setGeofenceEditMode(true);
          }
        }}
        className={`px-3 py-1.5 text-xs font-mono rounded transition-colors ${
          geofenceEditMode
            ? 'bg-nexus-amber/20 text-nexus-amber border border-nexus-amber/30'
            : 'bg-nexus-card text-nexus-text-secondary border border-nexus-border hover:text-nexus-text'
        }`}
      >
        {geofenceEditMode ? `Drawing (${geofenceVertices.length} pts)` : 'Draw Geofence'}
      </button>

      {geofenceEditMode && (
        <>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Geofence name"
            className="px-2 py-1 text-xs font-mono bg-nexus-bg border border-nexus-border rounded outline-none text-nexus-text placeholder:text-nexus-text-secondary w-32"
          />
          <select
            value={alertType}
            onChange={(e) => setAlertType(e.target.value as 'entry' | 'exit' | 'both')}
            className="px-2 py-1 text-xs font-mono bg-nexus-bg border border-nexus-border rounded outline-none text-nexus-text"
          >
            <option value="entry">Entry</option>
            <option value="exit">Exit</option>
            <option value="both">Both</option>
          </select>
          <button
            onClick={removeLastVertex}
            disabled={geofenceVertices.length === 0}
            className="px-2 py-1 text-xs font-mono text-nexus-text-secondary border border-nexus-border rounded hover:text-nexus-text disabled:opacity-30 transition-colors"
            title="Undo last vertex"
          >
            Undo
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || geofenceVertices.length < 3}
            className="px-2 py-1 text-xs font-mono bg-nexus-cyan/20 text-nexus-cyan rounded border border-nexus-cyan/30 disabled:opacity-30 transition-colors"
          >
            Save
          </button>
          <button
            onClick={handleCancel}
            className="px-2 py-1 text-xs font-mono text-red-400 border border-red-400/30 rounded hover:bg-red-400/10 transition-colors"
          >
            Cancel
          </button>
        </>
      )}

      {geofences.length > 0 && !geofenceEditMode && (
        <div className="flex items-center gap-1">
          <span className="text-[10px] font-mono text-nexus-text-secondary">
            {geofences.length} geofence{geofences.length !== 1 ? 's' : ''}
          </span>
          {geofences.map((gf) => (
            <button
              key={gf.id}
              onClick={() => removeGeofence(gf.id)}
              className="text-[9px] font-mono text-red-400/60 hover:text-red-400 transition-colors"
              title={`Remove ${gf.name}`}
            >
              x
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
