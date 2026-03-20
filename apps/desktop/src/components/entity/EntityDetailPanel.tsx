import { useState } from 'react';
import { clsx } from 'clsx';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useEntityStore } from '@/stores/useEntityStore';
import { ConfidenceBar } from '@/components/common/ConfidenceBar';
import { IntBadge } from '@/components/common/IntBadge';
import { Badge } from '@/components/common/Badge';
import { Button } from '@/components/common/Button';
import { OverviewTab } from './tabs/OverviewTab';
import { RelationsTab } from './tabs/RelationsTab';
import { RawDataTab } from './tabs/RawDataTab';
import { TrackingPanel, InferencePanel } from '@/components/ontology/TrackingView';
import { investigations, stix, entities as entitiesApi, ontology } from '@/services/api';

type Tab = 'overview' | 'relations' | 'timeline' | 'raw';
type PanelView = 'detail' | 'tracking' | 'reasoning' | 'dossier';

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'relations', label: 'Relations' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'raw', label: 'Raw Data' },
];

export function EntityDetailPanel() {
  const { selectedEntity, clearSelection } = useEntityStore();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [panelView, setPanelView] = useState<PanelView>('detail');

  const timelineQuery = useQuery({
    queryKey: ['entity', 'timeline', selectedEntity?.id],
    queryFn: () => entitiesApi.getTimeline(selectedEntity!.id),
    enabled: activeTab === 'timeline' && !!selectedEntity?.id,
    retry: false,
  });

  const trackingQuery = useQuery({
    queryKey: ['ontology', 'tracking', selectedEntity?.id],
    queryFn: () => ontology.getTracking(selectedEntity!.id),
    enabled: panelView === 'tracking' && !!selectedEntity?.id,
    retry: false,
  });

  const inferenceQuery = useQuery({
    queryKey: ['ontology', 'reason', selectedEntity?.id],
    queryFn: () => ontology.reason([selectedEntity!.id], 'infer'),
    enabled: panelView === 'reasoning' && !!selectedEntity?.id,
    retry: false,
  });

  const dossierMutation = useMutation({
    mutationFn: async () => {
      if (!selectedEntity) return;
      return await entitiesApi.generateDossier(selectedEntity.id);
    },
  });

  const suggestionsQuery = useQuery({
    queryKey: ['entity', 'suggestions', selectedEntity?.id],
    queryFn: () => entitiesApi.getSuggestions(selectedEntity!.id),
    enabled: panelView === 'dossier' && !!selectedEntity?.id,
    retry: false,
  });

  const investigateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedEntity) return;
      const inv = await investigations.create({
        query: selectedEntity.name,
        target_ints: [selectedEntity.sourceInt || 'CYBINT'],
        priority: 'high',
      }) as { id: string };
      await investigations.execute(inv.id);
      return inv;
    },
  });

  const exportMutation = useMutation({
    mutationFn: async () => {
      if (!selectedEntity) return;
      const bundle = await stix.exportEntity(selectedEntity.id);
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedEntity.name.replace(/[^a-zA-Z0-9]/g, '_')}_stix.json`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  if (!selectedEntity) {
    return (
      <div className="h-full flex items-center justify-center bg-nexus-bg-secondary">
        <p className="text-sm text-nexus-text-secondary">Select an entity to view details</p>
      </div>
    );
  }

  // Tracking view
  if (panelView === 'tracking') {
    if (trackingQuery.isLoading) {
      return (
        <div className="h-full flex items-center justify-center bg-nexus-bg-secondary">
          <div className="text-center">
            <div className="w-6 h-6 border-2 border-nexus-cyan/30 border-t-nexus-cyan rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs font-mono text-nexus-text-secondary">Building tracking chain...</p>
          </div>
        </div>
      );
    }
    if (trackingQuery.isError) {
      return (
        <div className="h-full flex flex-col items-center justify-center bg-nexus-bg-secondary gap-3">
          <p className="text-xs font-mono text-nexus-text-secondary">Tracking data unavailable</p>
          <button onClick={() => setPanelView('detail')} className="text-[10px] font-mono text-nexus-cyan hover:underline">Back</button>
        </div>
      );
    }
    if (trackingQuery.data) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return <TrackingPanel data={trackingQuery.data as any} onClose={() => setPanelView('detail')} />;
    }
  }

  // Dossier view
  if (panelView === 'dossier') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const dossierData = dossierMutation.data as any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const suggestionsData = suggestionsQuery.data as any;

    return (
      <div className="h-full flex flex-col bg-nexus-bg-secondary overflow-hidden">
        <div className="p-3 border-b border-nexus-border flex items-center justify-between">
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-nexus-cyan">
              Intelligence Dossier
            </h3>
            <p className="text-[10px] text-nexus-text-secondary mt-0.5">{selectedEntity?.name}</p>
          </div>
          <button
            onClick={() => setPanelView('detail')}
            className="text-nexus-text-secondary hover:text-nexus-text text-xs"
          >
            X
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {!dossierData && !dossierMutation.isPending && (
            <div className="text-center py-8">
              <button
                onClick={() => dossierMutation.mutate()}
                className="px-4 py-2 text-xs font-mono uppercase tracking-wider bg-nexus-cyan/20 text-nexus-cyan rounded border border-nexus-cyan/30 hover:bg-nexus-cyan/30 transition-colors"
              >
                Generate Dossier
              </button>
              <p className="text-[10px] text-nexus-text-secondary mt-2">
                Aggregates all intelligence data into a comprehensive briefing
              </p>
            </div>
          )}

          {dossierMutation.isPending && (
            <div className="text-center py-8">
              <div className="w-6 h-6 border-2 border-nexus-cyan/30 border-t-nexus-cyan rounded-full animate-spin mx-auto mb-2" />
              <p className="text-xs font-mono text-nexus-text-secondary">Generating dossier...</p>
              <p className="text-[10px] text-nexus-text-secondary/50 mt-1">
                Aggregating network, timeline, anomalies, and cross-INT data
              </p>
            </div>
          )}

          {dossierMutation.isError && (
            <div className="p-2 rounded bg-red-400/10 border border-red-400/30 text-red-400 text-xs">
              Failed to generate dossier. Check API connection.
            </div>
          )}

          {dossierData && (
            <>
              {/* Summary Stats */}
              {dossierData.data && (
                <div className="grid grid-cols-2 gap-1.5">
                  <div className="p-2 rounded bg-nexus-bg border border-nexus-border text-center">
                    <p className="text-sm font-mono text-nexus-cyan">{dossierData.data.connection_count}</p>
                    <p className="text-[8px] font-mono text-nexus-text-secondary">Connections</p>
                  </div>
                  <div className="p-2 rounded bg-nexus-bg border border-nexus-border text-center">
                    <p className="text-sm font-mono text-nexus-cyan">{dossierData.data.neighbor_count}</p>
                    <p className="text-[8px] font-mono text-nexus-text-secondary">Neighbors</p>
                  </div>
                  <div className="p-2 rounded bg-nexus-bg border border-nexus-border text-center">
                    <p className="text-sm font-mono text-nexus-cyan">{dossierData.data.timeline_events}</p>
                    <p className="text-[8px] font-mono text-nexus-text-secondary">Events</p>
                  </div>
                  <div className="p-2 rounded bg-nexus-bg border border-nexus-border text-center">
                    <p className="text-sm font-mono text-amber-400">{dossierData.data.anomaly_count}</p>
                    <p className="text-[8px] font-mono text-nexus-text-secondary">Anomalies</p>
                  </div>
                </div>
              )}

              {/* Dossier Markdown */}
              <div className="prose prose-invert prose-xs max-w-none">
                <div
                  className="text-[11px] font-mono leading-relaxed text-nexus-text whitespace-pre-wrap"
                >
                  {dossierData.dossier_markdown}
                </div>
              </div>

              {/* Regenerate */}
              <button
                onClick={() => dossierMutation.mutate()}
                disabled={dossierMutation.isPending}
                className="w-full py-1 text-[10px] font-mono uppercase tracking-wider border border-nexus-border text-nexus-text-secondary rounded hover:text-nexus-text hover:border-nexus-text-secondary transition-colors"
              >
                Regenerate
              </button>
            </>
          )}

          {/* Pivot Suggestions */}
          {suggestionsData?.suggestions && suggestionsData.suggestions.length > 0 && (
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary mb-1">
                Suggested Follow-ups
              </p>
              <div className="space-y-1">
                {suggestionsData.suggestions.map((s: { int_type: string; scan_type: string; query: string; reason: string }, i: number) => (
                  <div key={i} className="p-1.5 rounded bg-nexus-bg border border-nexus-border">
                    <div className="flex items-center gap-1">
                      <span className="text-[8px] font-mono text-nexus-cyan bg-nexus-cyan/10 px-1 rounded">
                        {s.int_type}
                      </span>
                      <span className="text-[9px] font-mono text-nexus-text">{s.scan_type}</span>
                    </div>
                    <p className="text-[9px] text-nexus-text-secondary mt-0.5">{s.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Reasoning view
  if (panelView === 'reasoning') {
    if (inferenceQuery.isLoading) {
      return (
        <div className="h-full flex items-center justify-center bg-nexus-bg-secondary">
          <div className="text-center">
            <div className="w-6 h-6 border-2 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs font-mono text-nexus-text-secondary">Running ontology reasoning...</p>
          </div>
        </div>
      );
    }
    if (inferenceQuery.isError) {
      return (
        <div className="h-full flex flex-col items-center justify-center bg-nexus-bg-secondary gap-3">
          <p className="text-xs font-mono text-nexus-text-secondary">Reasoning data unavailable</p>
          <button onClick={() => setPanelView('detail')} className="text-[10px] font-mono text-nexus-cyan hover:underline">Back</button>
        </div>
      );
    }
    if (inferenceQuery.data) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return <InferencePanel data={inferenceQuery.data as any} onClose={() => setPanelView('detail')} />;
    }
  }

  return (
    <div className="h-full flex flex-col bg-nexus-bg-secondary overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-nexus-border">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-nexus-cyan/20 flex items-center justify-center border border-nexus-cyan/30">
              <span className="text-xs font-mono text-nexus-cyan">
                {selectedEntity.type.slice(0, 2).toUpperCase()}
              </span>
            </div>
            <div>
              <h3 className="text-sm font-medium text-nexus-text">{selectedEntity.name}</h3>
              <div className="flex items-center gap-1.5 mt-0.5">
                <Badge variant="cyan">{selectedEntity.type}</Badge>
                <IntBadge intType={selectedEntity.sourceInt} />
              </div>
            </div>
          </div>
          <button
            onClick={clearSelection}
            className="text-nexus-text-secondary hover:text-nexus-text text-xs"
          >
            X
          </button>
        </div>

        {/* Confidence & Risk */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-nexus-text-secondary">Confidence</span>
            <span className="font-mono">{Math.round(selectedEntity.confidence * 100)}%</span>
          </div>
          <ConfidenceBar value={selectedEntity.confidence} showLabel={false} />
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-nexus-text-secondary">Risk Score</span>
            <span className="font-mono text-nexus-text">{selectedEntity.riskScore}/10</span>
          </div>
          <div className="h-1.5 bg-nexus-bg rounded-full overflow-hidden">
            <div
              className={clsx(
                'h-full rounded-full transition-all',
                selectedEntity.riskScore >= 8 ? 'bg-nexus-red' : selectedEntity.riskScore >= 5 ? 'bg-nexus-amber' : 'bg-nexus-green',
              )}
              style={{ width: `${selectedEntity.riskScore * 10}%` }}
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-nexus-border">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex-1 px-2 py-1.5 text-[11px] font-medium transition-colors',
              activeTab === tab.id
                ? 'text-nexus-cyan border-b border-nexus-cyan'
                : 'text-nexus-text-secondary hover:text-nexus-text',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'overview' && <OverviewTab entity={selectedEntity} />}
        {activeTab === 'relations' && <RelationsTab entityId={selectedEntity.id} />}
        {activeTab === 'timeline' && (
          <div className="p-3">
            {timelineQuery.isLoading && (
              <p className="text-xs font-mono text-nexus-text-secondary">Loading timeline...</p>
            )}
            {timelineQuery.data && Array.isArray(timelineQuery.data) && timelineQuery.data.length > 0 ? (
              <div className="space-y-2">
                {(timelineQuery.data as Array<{ timestamp: string; event: string; source: string }>).map((evt, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs">
                    <span className="text-[10px] font-mono text-nexus-text-secondary w-20 flex-shrink-0">
                      {new Date(evt.timestamp).toLocaleString()}
                    </span>
                    <div className="w-1.5 h-1.5 rounded-full bg-nexus-cyan mt-1 flex-shrink-0" />
                    <div>
                      <span className="font-mono text-nexus-text">{evt.event}</span>
                      {evt.source && (
                        <span className="ml-2 text-[10px] text-nexus-text-secondary">[{evt.source}]</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : !timelineQuery.isLoading && (
              <p className="text-xs font-mono text-nexus-text-secondary text-center py-4">No timeline events</p>
            )}
          </div>
        )}
        {activeTab === 'raw' && <RawDataTab entity={selectedEntity} />}
      </div>

      {/* Actions */}
      <div className="p-2 border-t border-nexus-border space-y-1.5">
        <div className="flex gap-1.5">
          <Button
            variant="primary"
            size="sm"
            className="flex-1"
            onClick={() => investigateMutation.mutate()}
            disabled={investigateMutation.isPending}
          >
            {investigateMutation.isPending ? 'Launching...' : investigateMutation.isError ? 'Access Denied' : 'Deep Investigate'}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending}
          >
            {exportMutation.isPending ? '...' : 'Export'}
          </Button>
        </div>
        <div className="flex gap-1.5">
          <button
            onClick={() => setPanelView('tracking')}
            className="flex-1 px-2 py-1.5 text-[10px] font-mono uppercase tracking-wider rounded border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
          >
            Track
          </button>
          <button
            onClick={() => setPanelView('reasoning')}
            className="flex-1 px-2 py-1.5 text-[10px] font-mono uppercase tracking-wider rounded border border-amber-500/30 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-colors"
          >
            Reason
          </button>
        </div>
        <button
          onClick={() => {
            setPanelView('dossier');
            dossierMutation.mutate();
          }}
          disabled={dossierMutation.isPending}
          className="w-full px-2 py-1.5 text-[10px] font-mono uppercase tracking-wider rounded border border-purple-500/30 bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 transition-colors disabled:opacity-40"
        >
          {dossierMutation.isPending ? 'Generating...' : 'Intel Dossier'}
        </button>
      </div>
    </div>
  );
}
