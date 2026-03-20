import { create } from 'zustand';
import { auth, setAccessToken } from '@/services/api';
import { tokenStorage } from '@/services/tokenStorage';

interface AuthUser {
  id: string;
  username: string;
  email: string;
  role: string;
}

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loginError: string | null;
  authScreen: 'login' | 'register';

  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, passwordConfirm: string) => Promise<void>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
  refreshTokens: () => Promise<boolean>;
  setLoginError: (error: string | null) => void;
  setAuthScreen: (screen: 'login' | 'register') => void;
}

let refreshToken: string | null = null;

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  loginError: null,
  authScreen: 'login',

  login: async (username: string, password: string) => {
    set({ loginError: null, isLoading: true });
    try {
      const response = await auth.login(username, password);
      setAccessToken(response.access_token);
      refreshToken = response.refresh_token;
      await tokenStorage.saveTokens(response.access_token, response.refresh_token);

      const user = await auth.me();
      set({
        user: user as AuthUser,
        isAuthenticated: true,
        isLoading: false,
        loginError: null,
      });
    } catch (err) {
      set({
        isLoading: false,
        loginError: err instanceof Error ? err.message : 'Login failed',
      });
      throw err;
    }
  },

  register: async (username: string, email: string, password: string, passwordConfirm: string) => {
    set({ loginError: null, isLoading: true });
    try {
      const response = await auth.register(username, email, password, passwordConfirm);
      setAccessToken(response.access_token);
      refreshToken = response.refresh_token;
      await tokenStorage.saveTokens(response.access_token, response.refresh_token);

      const user = await auth.me();
      set({
        user: user as AuthUser,
        isAuthenticated: true,
        isLoading: false,
        loginError: null,
      });
    } catch (err) {
      set({
        isLoading: false,
        loginError: err instanceof Error ? err.message : 'Registration failed',
      });
      throw err;
    }
  },

  logout: async () => {
    try {
      await auth.logout();
    } catch {
      // Best-effort server-side logout
    }
    setAccessToken(null);
    refreshToken = null;
    await tokenStorage.clearTokens();
    set({ user: null, isAuthenticated: false, loginError: null });
  },

  restoreSession: async () => {
    set({ isLoading: true });
    try {
      const tokens = await tokenStorage.loadTokens();
      if (!tokens) {
        set({ isLoading: false });
        return;
      }

      setAccessToken(tokens.accessToken);
      refreshToken = tokens.refreshToken;

      try {
        const user = await auth.me();
        set({ user: user as AuthUser, isAuthenticated: true, isLoading: false });
      } catch {
        // Access token expired — try refresh
        const refreshed = await get().refreshTokens();
        if (refreshed) {
          const user = await auth.me();
          set({ user: user as AuthUser, isAuthenticated: true, isLoading: false });
        } else {
          setAccessToken(null);
          refreshToken = null;
          await tokenStorage.clearTokens();
          set({ isLoading: false });
        }
      }
    } catch {
      set({ isLoading: false });
    }
  },

  refreshTokens: async () => {
    if (!refreshToken) return false;
    try {
      const response = await auth.refresh(refreshToken);
      setAccessToken(response.access_token);
      refreshToken = response.refresh_token;
      await tokenStorage.saveTokens(response.access_token, response.refresh_token);
      return true;
    } catch {
      return false;
    }
  },

  setLoginError: (error) => set({ loginError: error }),
  setAuthScreen: (screen) => set({ authScreen: screen, loginError: null }),
}));
