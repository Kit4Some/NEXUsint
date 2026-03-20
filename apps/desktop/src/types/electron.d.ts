export interface NexusAPI {
  minimize: () => void;
  maximize: () => void;
  close: () => void;
  isMaximized: () => Promise<boolean>;
  onInvestigationProgress: (callback: (data: unknown) => void) => void;
  onNewEntity: (callback: (data: unknown) => void) => void;
  onAlert: (callback: (data: unknown) => void) => void;
  removeAllListeners: (channel: string) => void;
  auth: {
    saveTokens: (accessToken: string, refreshToken: string) => Promise<boolean>;
    loadTokens: () => Promise<{ accessToken: string; refreshToken: string } | null>;
    clearTokens: () => Promise<boolean>;
  };
  updates: {
    checkForUpdates: () => void;
    installUpdate: () => void;
    onUpdateAvailable: (callback: (info: unknown) => void) => void;
    onDownloadProgress: (callback: (progress: unknown) => void) => void;
    onUpdateDownloaded: (callback: (info: unknown) => void) => void;
  };
}

declare global {
  interface Window {
    nexusAPI: NexusAPI;
  }
}
