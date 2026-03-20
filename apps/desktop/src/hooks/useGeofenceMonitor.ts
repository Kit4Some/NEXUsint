import { useEffect, useRef } from 'react';
import { useMapStore } from '@/stores/useMapStore';
import { pointInPolygon, interpolateTrackPosition } from '@/utils/geoUtils';

/**
 * Monitors active tracks against geofences and fires alerts
 * when entities enter or exit geofenced areas.
 */
export function useGeofenceMonitor() {
  const { activeTracks, geofences, playbackTime, playbackMaxTime } = useMapStore();
  const prevStates = useRef<Map<string, Map<string, boolean>>>(new Map());

  useEffect(() => {
    if (geofences.length === 0 || activeTracks.size === 0) return;

    const progress = playbackMaxTime > 0 ? playbackTime / playbackMaxTime : 0;
    const currentStates = new Map<string, Map<string, boolean>>();

    for (const [entityId, points] of activeTracks.entries()) {
      const pos = interpolateTrackPosition(points, progress);
      if (!pos) continue;

      const entityFenceStates = new Map<string, boolean>();

      for (const fence of geofences) {
        const coords = fence.polygon?.geometry?.coordinates?.[0] as [number, number][] | undefined;
        if (!coords || coords.length < 3) continue;

        const inside = pointInPolygon([pos.longitude, pos.latitude], coords);
        entityFenceStates.set(fence.id, inside);

        // Check transition
        const prevEntityStates = prevStates.current.get(entityId);
        const wasInside = prevEntityStates?.get(fence.id);

        if (wasInside !== undefined && wasInside !== inside) {
          const eventType = inside ? 'entry' : 'exit';
          const shouldAlert =
            fence.alertType === 'both' ||
            fence.alertType === eventType;

          if (shouldAlert) {
            const alertTitle = `Geofence ${eventType.toUpperCase()}: ${fence.name}`;
            const alertDesc = `Entity ${entityId} ${inside ? 'entered' : 'exited'} geofence "${fence.name}"`;

            // Push to monitoring store
            import('@/stores/useMonitoringStore').then(({ useMonitoringStore }) => {
              useMonitoringStore.getState().addAlert({
                id: `gf-alert-${Date.now()}-${entityId}`,
                entityId,
                entityName: entityId,
                alertType: 'geofence_breach',
                severity: 'high',
                title: alertTitle,
                description: alertDesc,
                createdAt: new Date().toISOString(),
              });
            }).catch(() => {});

            // Desktop notification
            if (Notification.permission === 'granted') {
              new Notification(alertTitle, { body: alertDesc });
            }
          }
        }
      }

      currentStates.set(entityId, entityFenceStates);
    }

    prevStates.current = currentStates;
  }, [activeTracks, geofences, playbackTime, playbackMaxTime]);
}
