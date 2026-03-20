import { useCallback, useEffect, useRef } from 'react';
import { collection } from '@/services/api';
import { useCollectionStore, type IntType } from '@/stores/useCollectionStore';
import { useAppStore } from '@/stores/useAppStore';

const SCAN_TYPES: Record<IntType, string[]> = {
  cybint: ['full', 'host', 'search', 'dns', 'whois', 'certificates', 'ip', 'domain'],
  socmint: ['keyword_search', 'user_timeline', 'user_info', 'username_search', 'channel_messages'],
  sigint: ['aircraft_state', 'area_aircraft', 'vessel_position', 'area_vessels'],
  geoint: ['satellite_search', 'osm_bbox', 'geocode_forward'],
};

export function getScanTypes(intType: IntType): string[] {
  return SCAN_TYPES[intType] || [];
}

export function useStartCollection() {
  const addJob = useCollectionStore((s) => s.addJob);

  return useCallback(
    async (intType: IntType, query: string, scanType: string, autoPivot = false) => {
      const collectFn = collection[intType];
      if (!collectFn) throw new Error(`Unknown INT type: ${intType}`);

      const result = (await collectFn({ query, scan_type: scanType, auto_pivot: autoPivot })) as {
        id: string;
        int_type: string;
        status: string;
        progress: number;
        result_count: number;
        created_at: string;
      };

      addJob({
        id: result.id,
        intType,
        query,
        scanType,
        status: result.status as 'queued' | 'running' | 'completed' | 'failed',
        progress: result.progress,
        resultCount: result.result_count,
        createdAt: result.created_at,
      });

      return result.id;
    },
    [addJob],
  );
}

export function useJobPoller() {
  const activeJobs = useCollectionStore((s) => s.activeJobs);
  const updateJob = useCollectionStore((s) => s.updateJob);
  const connectionStatus = useAppStore((s) => s.connectionStatus);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    const pendingJobs = Array.from(activeJobs.values()).filter(
      (j) => j.status === 'queued' || j.status === 'running',
    );

    if (pendingJobs.length === 0) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    // When WebSocket is connected, poll less frequently (fallback only)
    const pollInterval = connectionStatus === 'connected' ? 15000 : 3000;

    timerRef.current = setInterval(async () => {
      for (const job of pendingJobs) {
        try {
          const status = (await collection.getStatus(job.id)) as {
            status: string;
            progress: number;
            result_count: number;
            error?: string;
          };
          updateJob(job.id, {
            status: status.status as 'queued' | 'running' | 'completed' | 'failed',
            progress: status.progress,
            resultCount: status.result_count,
            error: status.error,
          });
        } catch {
          // API unreachable, skip
        }
      }
    }, pollInterval);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [activeJobs, updateJob, connectionStatus]);
}
