import { useState, useEffect } from 'react';
import { Command } from 'cmdk';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '@/stores/useAppStore';
import { useEntityStore } from '@/stores/useEntityStore';
import { useMapStore } from '@/stores/useMapStore';
import { useSearchSuggestions } from '@/hooks/useSearch';

const ITEM_CLASS = 'flex items-center gap-2 px-3 py-2 text-sm text-nexus-text rounded cursor-pointer data-[selected=true]:bg-nexus-cyan/10 data-[selected=true]:text-nexus-cyan';

export function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen, setActiveTab, setSearchOverlayOpen } = useAppStore();
  const { setDetailPanelOpen } = useEntityStore();
  const { setSelectedEntityId } = useMapStore();
  const [searchValue, setSearchValue] = useState('');

  const { data: suggestions } = useSearchSuggestions(searchValue);

  useEffect(() => {
    if (!commandPaletteOpen) setSearchValue('');
  }, [commandPaletteOpen]);

  return (
    <AnimatePresence>
      {commandPaletteOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setCommandPaletteOpen(false)}
          />

          {/* Command Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="relative w-[560px] glass-panel premium-border rounded-lg shadow-2xl overflow-hidden"
          >
            <Command className="w-full h-full">
              <Command.Input
                placeholder="Search entities, commands..."
                className="w-full px-4 py-3 bg-transparent text-sm text-nexus-text border-b border-nexus-border outline-none placeholder:text-nexus-text-secondary"
                value={searchValue}
                onValueChange={setSearchValue}
                autoFocus
              />

              <Command.List className="max-h-80 overflow-y-auto p-2">
                <Command.Empty className="px-4 py-8 text-center text-sm text-nexus-text-secondary">
                  No results found.
                </Command.Empty>

                {/* Live entity suggestions */}
                {suggestions && suggestions.length > 0 && (
                  <>
                    <Command.Group heading="Entities" className="text-[10px] uppercase tracking-wider text-nexus-text-secondary px-2 py-1">
                      {suggestions.map((s) => (
                        <Command.Item
                          key={s.id}
                          value={`entity-${s.name}`}
                          onSelect={() => {
                            setSelectedEntityId(s.id);
                            setDetailPanelOpen(true);
                            setCommandPaletteOpen(false);
                          }}
                          className={ITEM_CLASS}
                        >
                          <span className="text-nexus-cyan font-mono text-xs w-16 truncate">{s.type}</span>
                          {s.name}
                        </Command.Item>
                      ))}
                    </Command.Group>
                    <Command.Separator className="my-1 border-t border-nexus-border" />
                  </>
                )}

                <Command.Group heading="Navigation" className="text-[10px] uppercase tracking-wider text-nexus-text-secondary px-2 py-1">
                  <Command.Item
                    onSelect={() => { setActiveTab('map'); setCommandPaletteOpen(false); }}
                    className={ITEM_CLASS}
                  >
                    Map View
                    <kbd className="ml-auto text-[10px] px-1 py-0.5 rounded bg-nexus-bg border border-nexus-border font-mono">Ctrl+Shift+M</kbd>
                  </Command.Item>
                  <Command.Item
                    onSelect={() => { setActiveTab('graph'); setCommandPaletteOpen(false); }}
                    className={ITEM_CLASS}
                  >
                    Graph View
                    <kbd className="ml-auto text-[10px] px-1 py-0.5 rounded bg-nexus-bg border border-nexus-border font-mono">Ctrl+Shift+G</kbd>
                  </Command.Item>
                  <Command.Item
                    onSelect={() => { setActiveTab('dashboard'); setCommandPaletteOpen(false); }}
                    className={ITEM_CLASS}
                  >
                    Dashboard
                    <kbd className="ml-auto text-[10px] px-1 py-0.5 rounded bg-nexus-bg border border-nexus-border font-mono">Ctrl+Shift+D</kbd>
                  </Command.Item>
                </Command.Group>

                <Command.Separator className="my-1 border-t border-nexus-border" />

                <Command.Group heading="Actions" className="text-[10px] uppercase tracking-wider text-nexus-text-secondary px-2 py-1">
                  <Command.Item
                    onSelect={() => { setSearchOverlayOpen(true); setCommandPaletteOpen(false); }}
                    className={ITEM_CLASS}
                  >
                    Entity Search
                    <kbd className="ml-auto text-[10px] px-1 py-0.5 rounded bg-nexus-bg border border-nexus-border font-mono">Ctrl+/</kbd>
                  </Command.Item>
                  <Command.Item className={ITEM_CLASS}>
                    New Investigation
                  </Command.Item>
                  <Command.Item className={ITEM_CLASS}>
                    CYBINT Scan
                  </Command.Item>
                </Command.Group>
              </Command.List>
            </Command>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
