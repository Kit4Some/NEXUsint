import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('nexusAPI', {
  // Window controls
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  isMaximized: () => ipcRenderer.invoke('window:isMaximized'),

  // Investigation operations
  onInvestigationProgress: (callback: (data: unknown) => void) => {
    ipcRenderer.on('investigation:progress', (_event, data) => callback(data));
  },
  onNewEntity: (callback: (data: unknown) => void) => {
    ipcRenderer.on('entity:new', (_event, data) => callback(data));
  },
  onAlert: (callback: (data: unknown) => void) => {
    ipcRenderer.on('alert:received', (_event, data) => callback(data));
  },

  // Token storage (encrypted via safeStorage in main process)
  auth: {
    saveTokens: (accessToken: string, refreshToken: string) =>
      ipcRenderer.invoke('auth:saveTokens', accessToken, refreshToken),
    loadTokens: () => ipcRenderer.invoke('auth:loadTokens'),
    clearTokens: () => ipcRenderer.invoke('auth:clearTokens'),
  },

  // Auto-update
  updates: {
    checkForUpdates: () => ipcRenderer.invoke('update:check'),
    installUpdate: () => ipcRenderer.invoke('update:install'),
    onUpdateAvailable: (callback: (data: unknown) => void) => {
      ipcRenderer.on('update:available', (_event, data) => callback(data));
    },
    onDownloadProgress: (callback: (data: unknown) => void) => {
      ipcRenderer.on('update:progress', (_event, data) => callback(data));
    },
    onUpdateDownloaded: (callback: (data: unknown) => void) => {
      ipcRenderer.on('update:downloaded', (_event, data) => callback(data));
    },
  },

  // Cleanup
  removeAllListeners: (channel: string) => {
    ipcRenderer.removeAllListeners(channel);
  },
});
