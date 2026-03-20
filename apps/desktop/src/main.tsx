import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { luma } from '@luma.gl/core';
import { webgl2Adapter } from '@luma.gl/webgl';
import App from './App';
import './index.css';

// Register WebGL2 adapter explicitly — prevents luma.gl from attempting WebGPU
luma.registerAdapters([webgl2Adapter]);

// Suppress ResizeObserver loop errors (fired by deck.gl/luma.gl internals)
window.addEventListener('error', (event) => {
  if (
    event.message?.includes('ResizeObserver') ||
    event.message?.includes('maxTextureDimension2D') ||
    event.message?.includes('WebGL')
  ) {
    event.preventDefault();
    console.warn('[Suppressed GPU error]', event.message);
  }
});
window.addEventListener('unhandledrejection', (event) => {
  const msg = String(event.reason);
  if (msg.includes('maxTextureDimension2D') || msg.includes('WebGL') || msg.includes('luma.gl')) {
    event.preventDefault();
    console.warn('[Suppressed GPU promise rejection]', msg);
  }
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        // Don't retry on 4xx client errors (404, 403, 401, etc.)
        const msg = error instanceof Error ? error.message : String(error);
        if (/not found|forbidden|not authorized|Session expired/i.test(msg)) {
          return false;
        }
        return failureCount < 1; // max 1 retry for server errors
      },
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
