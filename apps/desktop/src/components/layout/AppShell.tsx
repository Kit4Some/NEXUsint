import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { TitleBar } from './TitleBar';
import { Sidebar } from './Sidebar';
import { TabBar } from './TabBar';
import { StatusBar } from './StatusBar';
import { CommandPalette } from './CommandPalette';
import { SearchOverlay } from '@/components/search/SearchOverlay';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { connectWebSocket, disconnectWebSocket } from '@/services/websocket';
import { useAppStore } from '@/stores/useAppStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { getAccessToken, API_HOST } from '@/services/api';
import { MapContainer } from '@/components/map/MapContainer';
import { GraphView } from '@/components/graph/GraphView';
import { TimelineView } from '@/components/timeline/TimelineView';
import { EntityDetailPanel } from '@/components/entity/EntityDetailPanel';
import { Dashboard } from '@/components/dashboard/Dashboard';
import { ReportView } from '@/components/report/ReportView';
import { StixPanel } from '@/components/stix/StixPanel';
import { MonitoringPanel } from '@/components/monitoring/MonitoringPanel';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { useEntityStore } from '@/stores/useEntityStore';
import { CollectionPanel } from '@/components/collection/CollectionPanel';
import { AIChatPanel } from '@/components/chat/AIChatPanel';
import { useChatStore } from '@/stores/useChatStore';
import { useLiveFeedStore } from '@/stores/useLiveFeedStore';

export function AppShell() {
  useKeyboardShortcuts();
  const { activeTab } = useAppStore();
  const { detailPanelOpen } = useEntityStore();
  const { isAuthenticated } = useAuthStore();
  const chatPanelOpen = useChatStore((s) => s.panelOpen);
  const toggleChat = useChatStore((s) => s.togglePanel);

  // Connect WebSocket only after user is authenticated (with JWT token)
  useEffect(() => {
    if (!isAuthenticated) return;
    const token = getAccessToken();
    if (!token) return;

    fetch(`${API_HOST}/health`, { signal: AbortSignal.timeout(3000) })
      .then(() => {
        connectWebSocket(token);
        // Auto-start live feed after WebSocket connects
        useLiveFeedStore.getState().startLiveFeed();
      })
      .catch(() => {
        // API not running — skip WebSocket, status bar will show disconnected
      });

    return () => {
      disconnectWebSocket();
    };
  }, [isAuthenticated]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col h-screen w-screen overflow-hidden bg-nexus-bg"
    >
      {/* Title Bar */}
      <TitleBar />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Sidebar + Collection Panel */}
        <Sidebar />
        <CollectionPanel />

        {/* Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tab Bar */}
          <TabBar />

          {/* Main Panel */}
          <PanelGroup direction="horizontal" className="flex-1" id="main-panel-group">
            <Panel id="main-content" order={1} defaultSize={detailPanelOpen ? 70 : 100} minSize={40}>
              <div className="h-full overflow-hidden relative">
                {activeTab === 'map' && <ErrorBoundary><MapContainer /></ErrorBoundary>}
                {activeTab === 'graph' && <ErrorBoundary><GraphView /></ErrorBoundary>}
                {activeTab === 'timeline' && <ErrorBoundary><TimelineView /></ErrorBoundary>}
                {activeTab === 'dashboard' && <ErrorBoundary><Dashboard /></ErrorBoundary>}
                {activeTab === 'report' && <ErrorBoundary><ReportView /></ErrorBoundary>}
                {activeTab === 'stix' && <ErrorBoundary><StixPanel /></ErrorBoundary>}
                {activeTab === 'monitoring' && <ErrorBoundary><MonitoringPanel /></ErrorBoundary>}
              </div>
            </Panel>

            {detailPanelOpen && !chatPanelOpen && (
              <>
                <PanelResizeHandle className="w-1 bg-nexus-border hover:bg-nexus-cyan/50 transition-colors cursor-col-resize z-50" />
                <Panel id="entity-detail" order={2} defaultSize={30} minSize={20} maxSize={50}>
                  <EntityDetailPanel />
                </Panel>
              </>
            )}
          </PanelGroup>
        </div>

        {/* AI Chat Panel */}
        <AIChatPanel />

        {/* Chat Toggle Button */}
        {!chatPanelOpen && (
          <button
            onClick={toggleChat}
            className="absolute bottom-10 right-3 z-50 w-9 h-9 rounded-full bg-nexus-cyan/20 border border-nexus-cyan/40 text-nexus-cyan flex items-center justify-center hover:bg-nexus-cyan/30 transition-colors shadow-lg shadow-nexus-cyan/10"
            title="Open AI Chat"
          >
            <span className="text-sm">💬</span>
          </button>
        )}
      </div>

      {/* Status Bar */}
      <StatusBar />

      {/* Command Palette */}
      <CommandPalette />

      {/* Search Overlay */}
      <SearchOverlay />

      {/* Scanline overlay */}
      <div className="scanline-overlay pointer-events-none" />
    </motion.div>
  );
}
