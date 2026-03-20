import { useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMapStore } from '@/stores/useMapStore';
import { formatPlaybackTime } from '@/utils/geoUtils';

const SPEED_OPTIONS = [0.5, 1, 2, 5, 10];

export function PlaybackControls() {
  const {
    activeTracks,
    playbackState,
    playbackTime,
    playbackMaxTime,
    playbackSpeed,
    liveFollow,
    togglePlayback,
    seekPlayback,
    setPlaybackSpeed,
    setLiveFollow,
  } = useMapStore();

  const scrubberRef = useRef<HTMLDivElement>(null);

  const handleScrub = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = scrubberRef.current?.getBoundingClientRect();
      if (!rect) return;
      const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      seekPlayback(ratio * playbackMaxTime);
    },
    [seekPlayback, playbackMaxTime],
  );

  const handleScrubDrag = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.buttons !== 1) return;
      handleScrub(e);
    },
    [handleScrub],
  );

  const skipToStart = useCallback(() => seekPlayback(0), [seekPlayback]);
  const skipToEnd = useCallback(() => {
    seekPlayback(playbackMaxTime);
    setLiveFollow(true);
  }, [seekPlayback, playbackMaxTime, setLiveFollow]);

  if (activeTracks.size === 0) return null;

  const progress = playbackMaxTime > 0 ? (playbackTime / playbackMaxTime) * 100 : 0;
  const trackCount = activeTracks.size;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        className="absolute bottom-10 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 px-3 py-2 bg-nexus-card/95 backdrop-blur-sm border border-nexus-border rounded-lg shadow-2xl shadow-black/40"
      >
        {/* Track count badge */}
        <div className="flex items-center gap-1 pr-2 border-r border-nexus-border">
          <div className="w-1.5 h-1.5 rounded-full bg-nexus-cyan animate-pulse" />
          <span className="text-[9px] font-mono text-nexus-text-secondary uppercase tracking-wider">
            {trackCount} trk
          </span>
        </div>

        {/* Skip to start */}
        <button
          onClick={skipToStart}
          className="w-6 h-6 flex items-center justify-center text-nexus-text-secondary hover:text-nexus-cyan transition-colors"
          title="Skip to start"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
            <rect x="0" y="1" width="2" height="8" />
            <polygon points="10,1 10,9 3,5" />
          </svg>
        </button>

        {/* Play / Pause */}
        <button
          onClick={togglePlayback}
          className="w-8 h-8 flex items-center justify-center rounded-full bg-nexus-cyan/20 border border-nexus-cyan/40 text-nexus-cyan hover:bg-nexus-cyan/30 transition-colors"
          title={playbackState === 'playing' ? 'Pause' : 'Play'}
        >
          {playbackState === 'playing' ? (
            <svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor">
              <rect x="1" y="0" width="3" height="12" rx="0.5" />
              <rect x="6" y="0" width="3" height="12" rx="0.5" />
            </svg>
          ) : (
            <svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor">
              <polygon points="1,0 10,6 1,12" />
            </svg>
          )}
        </button>

        {/* Skip to end */}
        <button
          onClick={skipToEnd}
          className="w-6 h-6 flex items-center justify-center text-nexus-text-secondary hover:text-nexus-cyan transition-colors"
          title="Skip to end (LIVE)"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
            <polygon points="0,1 0,9 7,5" />
            <rect x="8" y="1" width="2" height="8" />
          </svg>
        </button>

        {/* Scrubber */}
        <div
          ref={scrubberRef}
          className="relative w-40 h-5 flex items-center cursor-pointer group"
          onClick={handleScrub}
          onMouseMove={handleScrubDrag}
        >
          {/* Track */}
          <div className="absolute inset-y-0 left-0 right-0 flex items-center">
            <div className="w-full h-1 rounded-full bg-nexus-border">
              {/* Progress fill */}
              <div
                className="h-full rounded-full bg-gradient-to-r from-nexus-cyan/60 to-nexus-cyan transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
          {/* Thumb */}
          <div
            className="absolute w-3 h-3 rounded-full bg-nexus-cyan shadow-[0_0_6px_rgba(0,229,255,0.6)] border border-nexus-cyan/80 -translate-x-1/2 transition-transform group-hover:scale-125"
            style={{ left: `${progress}%` }}
          />
        </div>

        {/* Speed selector */}
        <div className="flex items-center gap-0.5">
          {SPEED_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setPlaybackSpeed(s)}
              className={`px-1.5 py-0.5 text-[9px] font-mono rounded transition-colors ${
                playbackSpeed === s
                  ? 'bg-nexus-cyan/30 text-nexus-cyan border border-nexus-cyan/40'
                  : 'text-nexus-text-secondary hover:text-nexus-text'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Time display */}
        <div className="text-[10px] font-mono text-nexus-text-secondary tabular-nums pl-1 border-l border-nexus-border">
          <span className="text-nexus-text">{formatPlaybackTime(playbackTime)}</span>
          <span className="mx-0.5">/</span>
          <span>{formatPlaybackTime(playbackMaxTime)}</span>
        </div>

        {/* LIVE toggle */}
        <button
          onClick={() => setLiveFollow(!liveFollow)}
          className={`px-2 py-0.5 text-[9px] font-mono uppercase tracking-widest rounded transition-colors ${
            liveFollow
              ? 'bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse'
              : 'text-nexus-text-secondary border border-nexus-border hover:text-nexus-text'
          }`}
          title={liveFollow ? 'Live mode ON — following latest data' : 'Live mode OFF — manual scrubbing'}
        >
          LIVE
        </button>
      </motion.div>
    </AnimatePresence>
  );
}
