import { useMapStore } from '@/stores/useMapStore';
import { Card } from '@/components/common/Card';

const LAYERS = [
  { id: 'entities', label: 'Entities', color: 'bg-nexus-cyan' },
  { id: 'connections', label: 'Connections', color: 'bg-nexus-purple' },
  { id: 'heatmap', label: 'Heatmap', color: 'bg-nexus-amber' },
  { id: 'flights', label: 'Flights', color: 'bg-orange-500' },
  { id: 'vessels', label: 'Vessels', color: 'bg-teal-500' },
  { id: 'geofence', label: 'Geofences', color: 'bg-nexus-green' },
  { id: 'satellite', label: 'Satellite', color: 'bg-emerald-500' },
  { id: 'osm', label: 'OSM Features', color: 'bg-sky-500' },
  { id: 'terrain', label: 'Terrain', color: 'bg-amber-700' },
  { id: 'liveFlights', label: 'Live Flights', color: 'bg-cyan-400' },
  { id: 'military', label: 'Military', color: 'bg-red-500' },
  { id: 'trackedAircraft', label: 'Tracked Aircraft', color: 'bg-amber-400' },
  { id: 'uavs', label: 'UAVs', color: 'bg-purple-500' },
  { id: 'earthquakes', label: 'Earthquakes', color: 'bg-yellow-600' },
  { id: 'activeFires', label: 'Fires', color: 'bg-orange-600' },
  { id: 'weatherRadar', label: 'Weather Radar', color: 'bg-blue-500' },
  { id: 'gpsJamming', label: 'GPS Jamming', color: 'bg-red-400' },
  { id: 'satellites', label: 'Satellites', color: 'bg-white' },
  { id: 'gdelt', label: 'GDELT Events', color: 'bg-orange-400' },
  { id: 'internetOutages', label: 'Internet Outages', color: 'bg-red-500' },
  { id: 'airports', label: 'Airports', color: 'bg-blue-400' },
  { id: 'militaryBases', label: 'Military Bases', color: 'bg-red-600' },
  { id: 'datacenters', label: 'Datacenters', color: 'bg-green-500' },
  { id: 'kiwisdr', label: 'KiwiSDR', color: 'bg-purple-400' },
];

export function LayerControl() {
  const { visibleLayers, toggleLayer } = useMapStore();

  return (
    <Card className="p-2 w-36">
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-2 px-1">
        Layers
      </p>
      <div className="space-y-1">
        {LAYERS.map((layer) => (
          <label
            key={layer.id}
            className="flex items-center gap-2 px-1 py-0.5 rounded hover:bg-nexus-bg cursor-pointer"
          >
            <input
              type="checkbox"
              checked={visibleLayers.has(layer.id)}
              onChange={() => toggleLayer(layer.id)}
              className="w-3 h-3 accent-[#00D4FF]"
            />
            <div className={`w-2 h-2 rounded-full ${layer.color}`} />
            <span className="text-xs text-nexus-text">{layer.label}</span>
          </label>
        ))}
      </div>
    </Card>
  );
}
