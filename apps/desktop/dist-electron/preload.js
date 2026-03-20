"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("nexusAPI", {
  // Window controls
  minimize: () => electron.ipcRenderer.send("window:minimize"),
  maximize: () => electron.ipcRenderer.send("window:maximize"),
  close: () => electron.ipcRenderer.send("window:close"),
  isMaximized: () => electron.ipcRenderer.invoke("window:isMaximized"),
  // Investigation operations
  onInvestigationProgress: (callback) => {
    electron.ipcRenderer.on("investigation:progress", (_event, data) => callback(data));
  },
  onNewEntity: (callback) => {
    electron.ipcRenderer.on("entity:new", (_event, data) => callback(data));
  },
  onAlert: (callback) => {
    electron.ipcRenderer.on("alert:received", (_event, data) => callback(data));
  },
  // Token storage (encrypted via safeStorage in main process)
  auth: {
    saveTokens: (accessToken, refreshToken) => electron.ipcRenderer.invoke("auth:saveTokens", accessToken, refreshToken),
    loadTokens: () => electron.ipcRenderer.invoke("auth:loadTokens"),
    clearTokens: () => electron.ipcRenderer.invoke("auth:clearTokens")
  },
  // Auto-update
  updates: {
    checkForUpdates: () => electron.ipcRenderer.invoke("update:check"),
    installUpdate: () => electron.ipcRenderer.invoke("update:install"),
    onUpdateAvailable: (callback) => {
      electron.ipcRenderer.on("update:available", (_event, data) => callback(data));
    },
    onDownloadProgress: (callback) => {
      electron.ipcRenderer.on("update:progress", (_event, data) => callback(data));
    },
    onUpdateDownloaded: (callback) => {
      electron.ipcRenderer.on("update:downloaded", (_event, data) => callback(data));
    }
  },
  // Cleanup
  removeAllListeners: (channel) => {
    electron.ipcRenderer.removeAllListeners(channel);
  }
});
