import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { useChatStore } from '@/stores/useChatStore';
import { useSendMessage, useExecuteAction } from '@/hooks/useChat';
import { useEntityStore } from '@/stores/useEntityStore';
import { useMapStore } from '@/stores/useMapStore';
import { useAppStore } from '@/stores/useAppStore';

const QUICK_COMMANDS = [
  { label: 'Collect', prefix: '/collect ', color: 'text-nexus-cyan' },
  { label: 'Analyze', prefix: '/analyze ', color: 'text-purple-400' },
  { label: 'Locate', prefix: '/locate ', color: 'text-green-400' },
  { label: 'Graph', prefix: '/graph ', color: 'text-amber-400' },
  { label: 'Threats', prefix: '/threats ', color: 'text-red-400' },
];

function MessageBubble({ msg, onExecuteAction }: {
  msg: { role: string; content: string; timestamp: string; entities?: Array<{ id: string; name: string; type: string }>; actions?: Array<{ type: string; label: string; params: Record<string, unknown> }> };
  onExecuteAction: (action: { type: string; label: string; params: Record<string, unknown> }) => void;
}) {
  const isUser = msg.role === 'user';
  const setSelectedEntity = useEntityStore((s) => s.setSelectedEntity);
  const { setViewState, setSelectedEntityId, setTrackingPanelOpen } = useMapStore();
  const { setActiveTab } = useAppStore();

  const handleAction = (action: { type: string; label: string; params: Record<string, unknown> }) => {
    switch (action.type) {
      case 'FLY_TO_TARGET':
      case 'FOCUS_ENTITY': {
        const lat = action.params.latitude as number | undefined;
        const lon = action.params.longitude as number | undefined;
        const id = action.params.entityId as string | undefined;
        if (id) setSelectedEntityId(id);
        if (lat !== undefined && lon !== undefined) {
          setViewState({ longitude: lon, latitude: lat, zoom: 12, pitch: 45, bearing: 0 });
          setActiveTab('map');
        }
        break;
      }
      case 'OPEN_TRACKING':
      case 'track': {
        const trackId = action.params.entity_id as string | undefined;
        if (trackId) setSelectedEntityId(trackId);
        setTrackingPanelOpen(true);
        setActiveTab('map');
        break;
      }
      case 'TRIGGER_COLLECTION':
      case 'CREATE_INVESTIGATION':
        onExecuteAction(action);
        break;
      case 'SHOW_SHORTEST_PATH':
        setActiveTab('graph');
        break;
      case 'investigate': {
        const invId = action.params.entity_id as string | undefined;
        if (invId) setSelectedEntityId(invId);
        onExecuteAction(action);
        break;
      }
      case 'anomaly':
      case 'centrality':
      case 'infer':
      case 'correlate':
        onExecuteAction(action);
        break;
      default:
        onExecuteAction(action);
        break;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}
    >
      <div
        className={clsx(
          'max-w-[85%] rounded-lg px-3 py-2 text-xs',
          isUser
            ? 'bg-nexus-cyan/20 text-nexus-text border border-nexus-cyan/30'
            : 'bg-nexus-card text-nexus-text border border-nexus-border',
        )}
      >
        <div className="whitespace-pre-wrap break-words">{msg.content}</div>

        {/* Entity references */}
        {msg.entities && msg.entities.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {msg.entities.map((e) => (
              <button
                key={e.id}
                onClick={() =>
                  setSelectedEntity({
                    id: e.id,
                    type: e.type,
                    name: e.name,
                    properties: {},
                    confidence: 0,
                    sourceInt: '',
                    riskScore: 0,
                    firstSeen: '',
                    lastSeen: '',
                  })
                }
                className="px-2 py-0.5 rounded text-[10px] font-mono bg-nexus-cyan/10 text-nexus-cyan border border-nexus-cyan/20 hover:bg-nexus-cyan/20 transition-colors"
              >
                {e.type}: {e.name}
              </button>
            ))}
          </div>
        )}

        {/* Suggested actions */}
        {msg.actions && msg.actions.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {msg.actions.map((a, i) => {
              const isExecutable = ['TRIGGER_COLLECTION', 'CREATE_INVESTIGATION', 'SHOW_SHORTEST_PATH', 'track', 'anomaly', 'centrality', 'infer', 'correlate', 'investigate'].includes(a.type);
              return (
                <button
                  key={i}
                  onClick={() => handleAction(a)}
                  className={clsx(
                    'px-2 py-0.5 rounded text-[10px] font-mono border transition-colors',
                    isExecutable
                      ? 'bg-nexus-cyan/15 text-nexus-cyan border-nexus-cyan/30 hover:bg-nexus-cyan/25'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/20 hover:bg-amber-500/20',
                  )}
                  title={`Execute: ${a.type}`}
                >
                  {isExecutable && <span className="mr-0.5">&gt; </span>}
                  {a.label}
                </button>
              );
            })}
          </div>
        )}

        <div className="text-[9px] text-nexus-text-secondary mt-1 text-right">
          {new Date(msg.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </motion.div>
  );
}

export function AIChatPanel() {
  const { messages, isLoading, contextEntityId, panelOpen, clearHistory, setContextEntity } = useChatStore();
  const sendMessage = useSendMessage();
  const executeAction = useExecuteAction();
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const selectedEntity = useEntityStore((s) => s.selectedEntity);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Sync context entity
  useEffect(() => {
    if (selectedEntity && selectedEntity.id !== contextEntityId) {
      setContextEntity(selectedEntity.id);
    }
  }, [selectedEntity, contextEntityId, setContextEntity]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!panelOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ width: 0, opacity: 0 }}
        animate={{ width: 340, opacity: 1 }}
        exit={{ width: 0, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className="h-full flex flex-col bg-nexus-bg-secondary border-l border-nexus-border overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-nexus-border bg-nexus-card/50">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-nexus-cyan shadow-[0_0_8px_rgba(0,229,255,0.6)] animate-pulse" />
            <span className="text-xs font-mono uppercase tracking-wider text-nexus-cyan">
              AI Analyst
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={clearHistory}
              className="text-[10px] text-nexus-text-secondary hover:text-nexus-text px-1.5 py-0.5 rounded hover:bg-nexus-card transition-colors"
              title="Clear chat"
            >
              Clear
            </button>
            <button
              onClick={() => useChatStore.getState().togglePanel()}
              className="text-nexus-text-secondary hover:text-nexus-text px-1 transition-colors"
            >
              X
            </button>
          </div>
        </div>

        {/* Context indicator */}
        {contextEntityId && (
          <div className="px-3 py-1.5 border-b border-nexus-border bg-nexus-cyan/5 flex items-center gap-2">
            <span className="text-[10px] text-nexus-text-secondary">Context:</span>
            <span className="text-[10px] font-mono text-nexus-cyan truncate">
              {selectedEntity?.name || contextEntityId}
            </span>
            <button
              onClick={() => setContextEntity(null)}
              className="text-[10px] text-nexus-text-secondary hover:text-nexus-text ml-auto"
            >
              X
            </button>
          </div>
        )}

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
          {messages.length === 0 && (
            <div className="text-center pt-8">
              <p className="text-sm font-mono text-nexus-cyan mb-1">NEXUS</p>
              <p className="text-xs text-nexus-text-secondary mb-3">
                AI-powered OSINT Analyst ready.
              </p>
              <div className="space-y-1.5">
                {[
                  'What threat actors are in the graph?',
                  'Collect CYBINT on suspicious IPs',
                  'Investigate APT-28 network',
                  'Find shortest path between targets',
                  'Show high-risk entities',
                  'Analyze network anomalies',
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => {
                      setInput(q);
                      inputRef.current?.focus();
                    }}
                    className="block w-full text-left px-3 py-1.5 rounded text-[10px] font-mono text-nexus-text-secondary hover:text-nexus-cyan hover:bg-nexus-card/50 border border-nexus-border/50 hover:border-nexus-cyan/30 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} onExecuteAction={executeAction} />
          ))}

          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-nexus-card border border-nexus-border rounded-lg px-3 py-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-nexus-cyan animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-nexus-cyan animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-nexus-cyan animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* Quick command buttons */}
        <div className="px-2 py-1.5 border-t border-nexus-border/50 flex items-center gap-1 overflow-x-auto">
          {QUICK_COMMANDS.map((cmd) => (
            <button
              key={cmd.label}
              onClick={() => {
                setInput(cmd.prefix);
                inputRef.current?.focus();
              }}
              className={clsx(
                'flex-shrink-0 px-2 py-0.5 rounded text-[9px] font-mono border border-nexus-border/50 hover:border-nexus-cyan/30 transition-colors',
                cmd.color,
              )}
            >
              {cmd.label}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="p-2 border-t border-nexus-border bg-nexus-card/30">
          <div className="flex gap-1.5">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask the AI analyst..."
              className="flex-1 bg-nexus-bg border border-nexus-border rounded px-3 py-1.5 text-xs text-nexus-text placeholder:text-nexus-text-secondary/50 focus:outline-none focus:border-nexus-cyan/50 transition-colors font-mono"
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="px-3 py-1.5 rounded text-xs font-mono bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/30 hover:bg-nexus-cyan/30 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
