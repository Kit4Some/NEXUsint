import { app, BrowserWindow, ipcMain, safeStorage } from 'electron';
import path from 'path';
import { initAutoUpdater } from './updater';
import { applySecurityHardening } from './security';

// Disable disk caching to prevent Access Denied errors during development
app.commandLine.appendSwitch('disable-http-cache');
app.commandLine.appendSwitch('disable-gpu-shader-disk-cache');
// Ensure WebGL works even on blocklisted GPUs (required for deck.gl/MapLibre)
app.commandLine.appendSwitch('ignore-gpu-blocklist');
app.commandLine.appendSwitch('enable-gpu-rasterization');
// Disable WebGPU to prevent luma.gl/deck.gl maxTextureDimension2D errors
app.commandLine.appendSwitch('disable-features', 'WebGPU');

// Ensure a clean user data path for dev to avoid locked cache db
if (process.env.VITE_DEV_SERVER_URL) {
  app.setPath('userData', path.join(app.getPath('userData'), 'nexus-dev'));
}

let mainWindow: BrowserWindow | null = null;

// Token storage (encrypted via safeStorage)
let encryptedTokens: Buffer | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 1000,
    minWidth: 1200,
    minHeight: 800,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0A0E1A',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
    },
  });

  // Apply security hardening
  applySecurityHardening(mainWindow);

  // Load Vite dev server in dev, built files in production
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Initialize auto-updater (production only)
  if (!process.env.VITE_DEV_SERVER_URL) {
    initAutoUpdater(mainWindow);
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Window controls IPC
ipcMain.on('window:minimize', () => mainWindow?.minimize());
ipcMain.on('window:maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});
ipcMain.on('window:close', () => mainWindow?.close());
ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() ?? false);

// Token storage IPC (encrypted with safeStorage)
ipcMain.handle('auth:saveTokens', (_event, accessToken: string, refreshToken: string) => {
  if (safeStorage.isEncryptionAvailable()) {
    const data = JSON.stringify({ accessToken, refreshToken });
    encryptedTokens = safeStorage.encryptString(data);
    return true;
  }
  return false;
});

ipcMain.handle('auth:loadTokens', () => {
  if (encryptedTokens && safeStorage.isEncryptionAvailable()) {
    try {
      const data = safeStorage.decryptString(encryptedTokens);
      return JSON.parse(data);
    } catch {
      encryptedTokens = null;
      return null;
    }
  }
  return null;
});

ipcMain.handle('auth:clearTokens', () => {
  encryptedTokens = null;
  return true;
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
