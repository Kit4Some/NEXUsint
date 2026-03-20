import { useState, useEffect } from 'react';

interface UpdateInfo {
  version: string;
  percent?: number;
}

export function UpdateNotification() {
  const [update, setUpdate] = useState<UpdateInfo | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const api = (window as any).nexusAPI;
    if (!api?.updates) return;

    api.updates.onUpdateAvailable((data: UpdateInfo) => {
      setUpdate(data);
    });

    api.updates.onDownloadProgress((data: { percent: number }) => {
      setDownloading(true);
      setProgress(Math.round(data.percent));
    });

    api.updates.onUpdateDownloaded((data: UpdateInfo) => {
      setDownloading(false);
      setDownloaded(true);
      setUpdate(data);
    });

    return () => {
      api.removeAllListeners?.('update:available');
      api.removeAllListeners?.('update:progress');
      api.removeAllListeners?.('update:downloaded');
    };
  }, []);

  if (!update) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 bg-nexus-accent/90 text-white rounded-lg px-4 py-3 shadow-lg max-w-sm">
      {downloading ? (
        <div>
          <p className="text-sm font-medium mb-2">
            Downloading update v{update.version}...
          </p>
          <div className="w-full bg-white/20 rounded-full h-2">
            <div
              className="bg-white rounded-full h-2 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs mt-1 opacity-80">{progress}%</p>
        </div>
      ) : downloaded ? (
        <div className="flex items-center gap-3">
          <p className="text-sm font-medium">
            Update v{update.version} ready
          </p>
          <button
            onClick={() => (window as any).nexusAPI?.updates?.installUpdate()}
            className="px-3 py-1 bg-white text-nexus-accent rounded text-sm font-medium hover:bg-white/90 transition-colors"
          >
            Restart
          </button>
        </div>
      ) : (
        <p className="text-sm">
          Update v{update.version} available — downloading...
        </p>
      )}
    </div>
  );
}
