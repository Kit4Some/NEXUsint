/**
 * Secure token persistence using Electron's safeStorage API.
 * Falls back to memory-only storage when safeStorage is unavailable.
 */

interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

const api = (window as any).nexusAPI;

export const tokenStorage = {
  async saveTokens(accessToken: string, refreshToken: string): Promise<void> {
    if (api?.auth?.saveTokens) {
      await api.auth.saveTokens(accessToken, refreshToken);
    }
  },

  async loadTokens(): Promise<StoredTokens | null> {
    if (api?.auth?.loadTokens) {
      return await api.auth.loadTokens();
    }
    return null;
  },

  async clearTokens(): Promise<void> {
    if (api?.auth?.clearTokens) {
      await api.auth.clearTokens();
    }
  },
};
