import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  entities?: Array<{ id: string; name: string; type: string }>;
  actions?: Array<{ type: string; label: string; params: Record<string, unknown> }>;
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  contextEntityId: string | null;
  panelOpen: boolean;
  sessionId: string;

  addMessage: (msg: ChatMessage) => void;
  updateLastAssistant: (content: string) => void;
  setLoading: (loading: boolean) => void;
  setContextEntity: (id: string | null) => void;
  togglePanel: () => void;
  setPanelOpen: (open: boolean) => void;
  clearHistory: () => void;
}

let _msgCounter = 0;
export function generateMsgId(): string {
  return `msg_${Date.now()}_${++_msgCounter}`;
}

function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,
  contextEntityId: null,
  panelOpen: false,
  sessionId: generateSessionId(),

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  updateLastAssistant: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant') {
          msgs[i] = { ...msgs[i], content };
          break;
        }
      }
      return { messages: msgs };
    }),

  setLoading: (loading) => set({ isLoading: loading }),
  setContextEntity: (id) => set({ contextEntityId: id }),
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  setPanelOpen: (open) => set({ panelOpen: open }),
  clearHistory: () => set({ messages: [], isLoading: false, sessionId: generateSessionId() }),
}));
