import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import electron from 'vite-plugin-electron';
import path from 'path';

// Stub Node.js builtins that are not available in sandboxed Electron renderer.
// @loaders.gl/worker-utils (deck.gl dep) imports child_process for Node worker-farm.
const NODE_BUILTINS_STUB = [
  'child_process',
  'worker_threads',
  'cluster',
  'dgram',
  'dns',
  'net',
  'tls',
];

function stubNodeBuiltins(): Plugin {
  return {
    name: 'stub-node-builtins',
    enforce: 'pre',
    resolveId(id) {
      if (NODE_BUILTINS_STUB.includes(id) || NODE_BUILTINS_STUB.includes(id.replace('node:', ''))) {
        return '\0node-builtin-stub';
      }
    },
    load(id) {
      if (id === '\0node-builtin-stub') {
        return 'export default {};';
      }
    },
  };
}

export default defineConfig({
  plugins: [
    stubNodeBuiltins(),
    react(),
    tailwindcss(),
    electron([
      {
        entry: 'electron/main.ts',
        vite: {
          build: {
            outDir: 'dist-electron',
            rollupOptions: {
              external: ['electron-updater', 'electron-log'],
            },
          },
        },
      },
      {
        entry: 'electron/preload.ts',
        onstart({ reload }) {
          reload();
        },
      },
    ]),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    esbuildOptions: {
      plugins: [
        {
          name: 'stub-node-builtins',
          setup(build) {
            const filter = new RegExp(`^(node:)?(${NODE_BUILTINS_STUB.join('|')})$`);
            build.onResolve({ filter }, (args) => ({
              path: args.path,
              namespace: 'node-builtin-stub',
            }));
            build.onLoad({ filter: /.*/, namespace: 'node-builtin-stub' }, () => ({
              contents: 'export default {}',
              loader: 'js',
            }));
          },
        },
      ],
    },
  },
  server: {
    port: 5173,
  },
});
