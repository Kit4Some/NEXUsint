import { useEffect } from 'react';
import { useAppStore } from '@/stores/useAppStore';

export function useKeyboardShortcuts() {
  const { setCommandPaletteOpen, setSearchOverlayOpen, setActiveTab } = useAppStore();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Ctrl+K — Command palette
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }

      // Ctrl+Shift+M — Map view
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'M') {
        e.preventDefault();
        setActiveTab('map');
      }

      // Ctrl+Shift+G — Graph view
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'G') {
        e.preventDefault();
        setActiveTab('graph');
      }

      // Ctrl+Shift+D — Dashboard
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        setActiveTab('dashboard');
      }

      // Ctrl+/ — Search overlay
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        setSearchOverlayOpen(true);
      }

      // Escape — Close command palette / search overlay
      if (e.key === 'Escape') {
        setCommandPaletteOpen(false);
        setSearchOverlayOpen(false);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setCommandPaletteOpen, setSearchOverlayOpen, setActiveTab]);
}
