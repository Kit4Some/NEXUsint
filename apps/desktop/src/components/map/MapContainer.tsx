import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMapStore, initAnimator, destroyAnimator } from '@/stores/useMapStore';
import { MapView } from './MapView';
import { GlobeView } from './GlobeView';
import { ViewModeToggle } from './controls/ViewModeToggle';
import { GeofenceToolbar } from './controls/GeofenceToolbar';
import { CrosshairCursor } from './controls/CrosshairCursor';
import { PlaybackControls } from './controls/PlaybackControls';
import { TrackingStatusOverlay } from './controls/TrackingStatusOverlay';
import { EntityInfoOverlay } from './popups/EntityInfoOverlay';
import { TrackingPanel } from '@/components/tracking/TrackingPanel';
import { FollowEntityControl } from './controls/FollowEntityControl';
import { useGeofenceMonitor } from '@/hooks/useGeofenceMonitor';
import NewsFeedPanel from '@/components/news/NewsFeedPanel';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';

export function MapContainer() {
  const { is3D, trackingPanelOpen, setTrackingPanelOpen, activeTracks, selectedEntityId } = useMapStore();
  const liveFeedNews = useLiveFeedStore((s) => s.news);

  // Initialize/destroy playback animator with component lifecycle
  useEffect(() => {
    initAnimator();
    return () => destroyAnimator();
  }, []);

  // Monitor geofence breaches
  useGeofenceMonitor();

  return (
    <div className="relative w-full h-full flex">
      <div className="flex-1 relative">
        {is3D ? <GlobeView /> : <MapView />}

        <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
          <ViewModeToggle />
          <GeofenceToolbar />
        </div>

        {/* Tracking panel toggle */}
        <button
          onClick={() => setTrackingPanelOpen(!trackingPanelOpen)}
          className="absolute top-3 right-40 z-10 px-3 py-1.5 text-[10px] uppercase tracking-widest font-mono glass-panel premium-border rounded text-nexus-text-secondary hover:text-nexus-cyan transition-colors"
        >
          {trackingPanelOpen ? 'Hide Tracks' : 'Tracks'}
        </button>

        {/* Tracking Status Overlay — top-left status panel */}
        {activeTracks.size > 0 && <TrackingStatusOverlay />}

        {/* Entity Info Overlay — shown when entity is selected */}
        {selectedEntityId && <EntityInfoOverlay />}

        {/* Follow entity control — shown when tracked entity is selected */}
        <FollowEntityControl />

        {/* Playback Controls — shown when tracks are active */}
        <PlaybackControls />

        {/* Live News Feed Overlay — bottom-right of map */}
        {liveFeedNews.length > 0 && (
          <div className="absolute bottom-14 right-3 z-20 w-80 max-h-[50vh]">
            <NewsFeedPanel />
          </div>
        )}

        {/* Interactive OSINT Cursor */}
        <CrosshairCursor />
      </div>

      <AnimatePresence>
        {trackingPanelOpen && (
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 50 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="w-64 flex-shrink-0 z-20 relative glass-panel premium-border border-r-0 border-y-0"
          >
            <TrackingPanel />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
