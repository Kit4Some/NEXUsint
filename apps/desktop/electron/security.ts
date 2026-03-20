import { app, session, BrowserWindow } from 'electron';

export function applySecurityHardening(win: BrowserWindow) {
  const isDev = !!process.env.VITE_DEV_SERVER_URL;

  // Dev CSP: allow Vite HMR inline scripts + wildcard localhost ports
  // Prod CSP: strict script-src, restricted connect-src
  const csp = isDev
    ? [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' data: https://fonts.gstatic.com",
        "img-src 'self' data: https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com blob:",
        "connect-src 'self' http://localhost:* ws://localhost:* https://basemaps.cartocdn.com https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org https://tiles.stadiamaps.com https://fonts.openmaptiles.org",
        "worker-src 'self' blob:",
      ].join('; ')
    : [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' data: https://fonts.gstatic.com",
        "img-src 'self' data: https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com blob:",
        "connect-src 'self' http://localhost:8000 ws://localhost:8000 https://basemaps.cartocdn.com https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org https://tiles.stadiamaps.com https://fonts.openmaptiles.org",
        "worker-src 'self' blob:",
      ].join('; ');

  // Enforce Content Security Policy
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [csp],
      },
    });
  });

  // Prevent navigation to external URLs
  win.webContents.on('will-navigate', (event, url) => {
    const appUrl = process.env.VITE_DEV_SERVER_URL || 'file://';
    if (!url.startsWith(appUrl) && !url.startsWith('file://')) {
      event.preventDefault();
    }
  });

  // Block new window creation
  win.webContents.setWindowOpenHandler(() => {
    return { action: 'deny' };
  });

  // Disable remote module
  app.on('remote-require', (event) => event.preventDefault());
  app.on('remote-get-builtin', (event) => event.preventDefault());
  app.on('remote-get-global', (event) => event.preventDefault());
  app.on('remote-get-current-window', (event) => event.preventDefault());
  app.on('remote-get-current-web-contents', (event) => event.preventDefault());
}
