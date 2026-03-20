import { useState, useEffect } from 'react';

export function TitleBar() {
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    window.nexusAPI?.isMaximized().then(setIsMaximized);
  }, []);

  return (
    <div className="flex items-center h-8 bg-nexus-bg select-none" style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}>
      {/* Logo & Title */}
      <div className="flex items-center gap-2 px-3">
        <div className="w-4 h-4 rounded bg-nexus-cyan glow-cyan" />
        <span className="text-xs font-heading font-bold tracking-wider text-nexus-cyan text-glow-cyan">
          NEXUS OSINT
        </span>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Window Controls */}
      <div className="flex" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
        <button
          onClick={() => window.nexusAPI?.minimize()}
          className="w-10 h-8 flex items-center justify-center hover:bg-nexus-card transition-colors"
        >
          <svg width="10" height="1" viewBox="0 0 10 1" fill="currentColor" className="text-nexus-text-secondary">
            <rect width="10" height="1" />
          </svg>
        </button>
        <button
          onClick={() => {
            window.nexusAPI?.maximize();
            setIsMaximized(!isMaximized);
          }}
          className="w-10 h-8 flex items-center justify-center hover:bg-nexus-card transition-colors"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" className="text-nexus-text-secondary">
            {isMaximized ? (
              <>
                <rect x="2" y="0" width="8" height="8" strokeWidth="1" />
                <rect x="0" y="2" width="8" height="8" strokeWidth="1" fill="var(--color-nexus-bg)" />
              </>
            ) : (
              <rect x="0.5" y="0.5" width="9" height="9" strokeWidth="1" />
            )}
          </svg>
        </button>
        <button
          onClick={() => window.nexusAPI?.close()}
          className="w-10 h-8 flex items-center justify-center hover:bg-nexus-red transition-colors"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" stroke="currentColor" className="text-nexus-text-secondary">
            <line x1="0" y1="0" x2="10" y2="10" strokeWidth="1" />
            <line x1="10" y1="0" x2="0" y2="10" strokeWidth="1" />
          </svg>
        </button>
      </div>
    </div>
  );
}
