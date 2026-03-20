import { useMapStore } from '@/stores/useMapStore';

export function FollowEntityControl() {
  const {
    selectedEntityId, followEntityId, followMode,
    setFollowEntity, setFollowMode, activeTracks,
  } = useMapStore();

  const entityId = selectedEntityId;
  if (!entityId || !activeTracks.has(entityId)) return null;

  const isFollowing = followEntityId === entityId && followMode !== 'off';

  return (
    <div className="absolute bottom-12 left-3 z-20 flex items-center gap-1.5">
      <button
        onClick={() => {
          if (isFollowing) {
            setFollowEntity(null);
            setFollowMode('off');
          } else {
            setFollowEntity(entityId);
            setFollowMode('center');
            // Immediately fly to entity position
            const track = activeTracks.get(entityId);
            if (track && track.length > 0) {
              const latest = track[track.length - 1];
              useMapStore.getState().setViewState({
                longitude: latest.position.longitude,
                latitude: latest.position.latitude,
                zoom: Math.max(useMapStore.getState().viewState.zoom, 12),
              });
            }
          }
        }}
        className={`px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider rounded border transition-colors ${
          isFollowing
            ? 'bg-nexus-cyan/20 text-nexus-cyan border-nexus-cyan/40'
            : 'bg-nexus-card/90 text-nexus-text-secondary border-nexus-border hover:text-nexus-cyan hover:border-nexus-cyan/30'
        }`}
      >
        {isFollowing ? 'Following' : 'Follow'}
      </button>
      {isFollowing && (
        <button
          onClick={() => setFollowMode(followMode === 'track' ? 'center' : 'track')}
          className={`px-2 py-1 text-[10px] font-mono rounded border transition-colors ${
            followMode === 'track'
              ? 'bg-amber-400/20 text-amber-400 border-amber-400/40'
              : 'bg-nexus-card/90 text-nexus-text-secondary border-nexus-border hover:text-amber-400 hover:border-amber-400/30'
          }`}
        >
          {followMode === 'track' ? 'Track HDG' : 'Center Only'}
        </button>
      )}
    </div>
  );
}
