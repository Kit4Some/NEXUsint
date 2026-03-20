import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useAuthStore } from '@/stores/useAuthStore';

export function LoginScreen() {
  const { login, isLoading, loginError, setAuthScreen } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const usernameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    usernameRef.current?.focus();
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username || !password || isLoading) return;
    try {
      await login(username, password);
    } catch {
      // Error is set in store
    }
  };

  return (
    <div className="flex items-center justify-center h-screen w-screen bg-[#0A0E1A]">
      <div className="w-full max-w-sm">
        {/* Branding */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-heading font-bold text-nexus-cyan tracking-wider">
            NEXUS
          </h1>
          <p className="text-nexus-text-secondary text-sm mt-1 tracking-widest uppercase">
            OSINT Intelligence Platform
          </p>
        </div>

        {/* Login Card */}
        <form
          onSubmit={handleSubmit}
          className="bg-nexus-card border border-nexus-border rounded-lg p-6 space-y-4"
        >
          <div>
            <label className="block text-nexus-text-secondary text-xs uppercase tracking-wider mb-1.5">
              Username
            </label>
            <input
              ref={usernameRef}
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading}
              className="w-full bg-nexus-bg border border-nexus-border rounded px-3 py-2 text-nexus-text font-mono text-sm focus:outline-none focus:border-nexus-cyan/50 focus:ring-1 focus:ring-nexus-cyan/30 disabled:opacity-50 placeholder:text-nexus-text-secondary/40"
              placeholder="analyst"
              autoComplete="username"
            />
          </div>

          <div>
            <label className="block text-nexus-text-secondary text-xs uppercase tracking-wider mb-1.5">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              className="w-full bg-nexus-bg border border-nexus-border rounded px-3 py-2 text-nexus-text font-mono text-sm focus:outline-none focus:border-nexus-cyan/50 focus:ring-1 focus:ring-nexus-cyan/30 disabled:opacity-50 placeholder:text-nexus-text-secondary/40"
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          {loginError && (
            <div className="text-nexus-red text-sm font-mono bg-nexus-red/10 border border-nexus-red/20 rounded px-3 py-2">
              {loginError}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !username || !password}
            className="w-full py-2.5 bg-nexus-cyan/10 text-nexus-cyan border border-nexus-cyan/30 rounded font-medium text-sm hover:bg-nexus-cyan/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <span className="w-4 h-4 border-2 border-nexus-cyan/30 border-t-nexus-cyan rounded-full animate-spin" />
                Authenticating...
              </>
            ) : (
              'Sign In'
            )}
          </button>

          <div className="text-center pt-1">
            <button
              type="button"
              onClick={() => setAuthScreen('register')}
              className="text-nexus-text-secondary text-xs hover:text-nexus-cyan transition-colors"
            >
              Don't have an account? <span className="text-nexus-cyan">Create Account</span>
            </button>
          </div>
        </form>

        {/* Version */}
        <p className="text-nexus-text-secondary/40 text-xs text-center mt-4 font-mono">
          v0.2.0
        </p>
      </div>
    </div>
  );
}
