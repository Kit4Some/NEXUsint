"use strict";
const electron = require("electron");
const path = require("path");
const electronUpdater = require("electron-updater");
const log = require("electron-log");
electronUpdater.autoUpdater.logger = log;
electronUpdater.autoUpdater.autoDownload = true;
electronUpdater.autoUpdater.autoInstallOnAppQuit = true;
let mainWindow$1 = null;
function initAutoUpdater(win) {
  mainWindow$1 = win;
  electronUpdater.autoUpdater.on("checking-for-update", () => {
    log.info("Checking for updates...");
  });
  electronUpdater.autoUpdater.on("update-available", (info) => {
    log.info("Update available:", info.version);
    mainWindow$1 == null ? void 0 : mainWindow$1.webContents.send("update:available", {
      version: info.version,
      releaseDate: info.releaseDate
    });
  });
  electronUpdater.autoUpdater.on("update-not-available", () => {
    log.info("No updates available");
  });
  electronUpdater.autoUpdater.on("download-progress", (progress) => {
    mainWindow$1 == null ? void 0 : mainWindow$1.webContents.send("update:progress", {
      percent: progress.percent,
      bytesPerSecond: progress.bytesPerSecond,
      transferred: progress.transferred,
      total: progress.total
    });
  });
  electronUpdater.autoUpdater.on("update-downloaded", (info) => {
    log.info("Update downloaded:", info.version);
    mainWindow$1 == null ? void 0 : mainWindow$1.webContents.send("update:downloaded", {
      version: info.version
    });
  });
  electronUpdater.autoUpdater.on("error", (err) => {
    log.error("Update error:", err);
    mainWindow$1 == null ? void 0 : mainWindow$1.webContents.send("update:error", { message: err.message });
  });
  electron.ipcMain.handle("update:check", () => electronUpdater.autoUpdater.checkForUpdates());
  electron.ipcMain.handle("update:install", () => electronUpdater.autoUpdater.quitAndInstall());
  setTimeout(() => electronUpdater.autoUpdater.checkForUpdates(), 5e3);
  setInterval(() => electronUpdater.autoUpdater.checkForUpdates(), 4 * 60 * 60 * 1e3);
}
function applySecurityHardening(win) {
  const isDev = !!process.env.VITE_DEV_SERVER_URL;
  const csp = isDev ? [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' data: https://fonts.gstatic.com",
    "img-src 'self' data: https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com blob:",
    "connect-src 'self' http://localhost:* ws://localhost:* https://basemaps.cartocdn.com https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org https://tiles.stadiamaps.com https://fonts.openmaptiles.org",
    "worker-src 'self' blob:"
  ].join("; ") : [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' data: https://fonts.gstatic.com",
    "img-src 'self' data: https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com blob:",
    "connect-src 'self' http://localhost:8000 ws://localhost:8000 https://basemaps.cartocdn.com https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org https://tiles.stadiamaps.com https://fonts.openmaptiles.org",
    "worker-src 'self' blob:"
  ].join("; ");
  electron.session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        "Content-Security-Policy": [csp]
      }
    });
  });
  win.webContents.on("will-navigate", (event, url) => {
    const appUrl = process.env.VITE_DEV_SERVER_URL || "file://";
    if (!url.startsWith(appUrl) && !url.startsWith("file://")) {
      event.preventDefault();
    }
  });
  win.webContents.setWindowOpenHandler(() => {
    return { action: "deny" };
  });
  electron.app.on("remote-require", (event) => event.preventDefault());
  electron.app.on("remote-get-builtin", (event) => event.preventDefault());
  electron.app.on("remote-get-global", (event) => event.preventDefault());
  electron.app.on("remote-get-current-window", (event) => event.preventDefault());
  electron.app.on("remote-get-current-web-contents", (event) => event.preventDefault());
}
electron.app.commandLine.appendSwitch("disable-http-cache");
electron.app.commandLine.appendSwitch("disable-gpu-shader-disk-cache");
electron.app.commandLine.appendSwitch("ignore-gpu-blocklist");
electron.app.commandLine.appendSwitch("enable-gpu-rasterization");
electron.app.commandLine.appendSwitch("disable-features", "WebGPU");
if (process.env.VITE_DEV_SERVER_URL) {
  electron.app.setPath("userData", path.join(electron.app.getPath("userData"), "nexus-dev"));
}
let mainWindow = null;
let encryptedTokens = null;
function createWindow() {
  mainWindow = new electron.BrowserWindow({
    width: 1600,
    height: 1e3,
    minWidth: 1200,
    minHeight: 800,
    frame: false,
    titleBarStyle: "hidden",
    backgroundColor: "#0A0E1A",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true
    }
  });
  applySecurityHardening(mainWindow);
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }
  if (!process.env.VITE_DEV_SERVER_URL) {
    initAutoUpdater(mainWindow);
  }
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}
electron.ipcMain.on("window:minimize", () => mainWindow == null ? void 0 : mainWindow.minimize());
electron.ipcMain.on("window:maximize", () => {
  if (mainWindow == null ? void 0 : mainWindow.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow == null ? void 0 : mainWindow.maximize();
  }
});
electron.ipcMain.on("window:close", () => mainWindow == null ? void 0 : mainWindow.close());
electron.ipcMain.handle("window:isMaximized", () => (mainWindow == null ? void 0 : mainWindow.isMaximized()) ?? false);
electron.ipcMain.handle("auth:saveTokens", (_event, accessToken, refreshToken) => {
  if (electron.safeStorage.isEncryptionAvailable()) {
    const data = JSON.stringify({ accessToken, refreshToken });
    encryptedTokens = electron.safeStorage.encryptString(data);
    return true;
  }
  return false;
});
electron.ipcMain.handle("auth:loadTokens", () => {
  if (encryptedTokens && electron.safeStorage.isEncryptionAvailable()) {
    try {
      const data = electron.safeStorage.decryptString(encryptedTokens);
      return JSON.parse(data);
    } catch {
      encryptedTokens = null;
      return null;
    }
  }
  return null;
});
electron.ipcMain.handle("auth:clearTokens", () => {
  encryptedTokens = null;
  return true;
});
electron.app.whenReady().then(createWindow);
electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    electron.app.quit();
  }
});
electron.app.on("activate", () => {
  if (electron.BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
