import { useMapStore } from '@/stores/useMapStore';

export function ViewModeToggle() {
  const { is3D, setIs3D } = useMapStore();

  return (
    <button
      onClick={() => setIs3D(!is3D)}
      className="bg-nexus-card/90 border border-nexus-border rounded-lg px-3 py-1.5 text-xs font-mono text-nexus-text-secondary hover:text-nexus-cyan hover:border-nexus-cyan/40 transition-colors backdrop-blur-sm"
      title={is3D ? 'Switch to 2D map' : 'Switch to 3D globe'}
    >
      {is3D ? '2D' : '3D'}
    </button>
  );
}
