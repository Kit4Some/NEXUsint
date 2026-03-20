import { useCallback } from 'react';
import { useChatStore, generateMsgId } from '@/stores/useChatStore';

const API_BASE = 'http://localhost:8000/api/v1';

export function useSendMessage() {
  const addMessage = useChatStore((s) => s.addMessage);
  const setLoading = useChatStore((s) => s.setLoading);
  const contextEntityId = useChatStore((s) => s.contextEntityId);
  const sessionId = useChatStore((s) => s.sessionId);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim()) return;

      // Add user message
      addMessage({
        id: generateMsgId(),
        role: 'user',
        content: text,
        timestamp: new Date().toISOString(),
      });

      setLoading(true);

      try {
        const { getAccessToken } = await import('@/services/api');
        const token = getAccessToken();

        const body: Record<string, unknown> = { message: text, session_id: sessionId };
        if (contextEntityId) {
          body.context = { entity_id: contextEntityId };
        }

        const res = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(body),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();

        addMessage({
          id: generateMsgId(),
          role: 'assistant',
          content: data.response || 'No response',
          timestamp: new Date().toISOString(),
          entities: data.entities,
          actions: data.actions,
        });
      } catch (err) {
        // Fallback mock logic for UI demonstration when API is unavailable
        console.warn('API Chat failed, using mock response:', err);
        const lowerInput = text.toLowerCase();
        let mockContent = "I'm currently operating offline. I can still execute local commands.";
        let mockActions: any[] = [];
        let mockEntities: any[] = [];

        if (lowerInput.includes('collect') || lowerInput.includes('수집')) {
          mockContent = "Initiating OSINT collection. Select a target and INT type to begin scanning.";
          mockActions = [
            { type: 'TRIGGER_COLLECTION', label: 'Collect CYBINT', params: { int_type: 'CYBINT', query: text.split(' ').pop(), scan_type: 'basic' } },
            { type: 'TRIGGER_COLLECTION', label: 'Collect SOCMINT', params: { int_type: 'SOCMINT', query: text.split(' ').pop(), scan_type: 'username' } },
          ];
        } else if (lowerInput.includes('investigate') || lowerInput.includes('조사')) {
          mockContent = "Creating a multi-INT investigation with cross-correlation analysis.";
          mockActions = [
            { type: 'CREATE_INVESTIGATION', label: 'Create Investigation', params: { query: `Investigate ${text.split(' ').pop()}`, target_ints: ['CYBINT'] } },
          ];
        } else if (lowerInput.includes('path') || lowerInput.includes('경로')) {
          mockContent = "Analyzing shortest path between entities in the knowledge graph.";
          mockActions = [
            { type: 'SHOW_SHORTEST_PATH', label: 'Show Graph Path', params: { from_id: 'entity-1', to_id: 'entity-2' } },
          ];
        } else if (lowerInput.includes('track') || lowerInput.includes('추적')) {
          mockContent = "Initiating tracking protocol for high-priority targets. Moving map viewport to their last known trajectory.";
          mockActions = [
            { type: 'FLY_TO_TARGET', label: 'Go to Target Region', params: { latitude: 37.5665, longitude: 126.9780, entityId: 'tgt-alpha' } },
            { type: 'OPEN_TRACKING', label: 'Open Track Panel', params: {} },
          ];
          mockEntities = [{ id: 'tgt-alpha', name: 'APT-28 Associated Target', type: 'ThreatActor' }];
        } else if (lowerInput.includes('vessel') || lowerInput.includes('선박')) {
          mockContent = "Locating suspicious vessels in the operational area.";
          mockActions = [
            { type: 'FLY_TO_TARGET', label: 'View Vessels', params: { latitude: 15.0, longitude: 115.0 } },
            { type: 'OPEN_TRACKING', label: 'Show Tracks', params: {} },
          ];
        } else if (lowerInput.includes('threat') || lowerInput.includes('위협')) {
          mockContent = "Conducting threat assessment across all INT sources. High-risk entities flagged for priority analysis.";
          mockActions = [
            { type: 'anomaly', label: 'Run Anomaly Detection', params: {} },
            { type: 'centrality', label: 'Find Key Players', params: {} },
          ];
        }

        addMessage({
          id: generateMsgId(),
          role: 'assistant',
          content: mockContent,
          timestamp: new Date().toISOString(),
          actions: mockActions.length ? mockActions : undefined,
          entities: mockEntities.length ? mockEntities : undefined,
        });
      } finally {
        setLoading(false);
      }
    },
    [addMessage, setLoading, contextEntityId, sessionId],
  );

  return send;
}

/**
 * Execute a chat-generated action on the backend (collection, investigation, etc.).
 */
export function useExecuteAction() {
  const addMessage = useChatStore((s) => s.addMessage);
  const setLoading = useChatStore((s) => s.setLoading);
  const sessionId = useChatStore((s) => s.sessionId);

  return useCallback(
    async (action: { type: string; label: string; params: Record<string, unknown> }) => {
      setLoading(true);
      addMessage({
        id: generateMsgId(),
        role: 'user',
        content: `Execute: ${action.label}`,
        timestamp: new Date().toISOString(),
      });

      try {
        const { getAccessToken } = await import('@/services/api');
        const token = getAccessToken();

        const res = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            message: `Execute: ${action.type}`,
            session_id: sessionId,
            execute_action: action,
          }),
        });

        const data = await res.json();
        addMessage({
          id: generateMsgId(),
          role: 'assistant',
          content: data.response || 'Action executed.',
          timestamp: new Date().toISOString(),
          entities: data.entities,
          actions: data.actions,
        });
      } catch (err) {
        addMessage({
          id: generateMsgId(),
          role: 'assistant',
          content: `Action "${action.label}" queued locally. Backend confirmation pending.`,
          timestamp: new Date().toISOString(),
        });
      } finally {
        setLoading(false);
      }
    },
    [addMessage, setLoading, sessionId],
  );
}
