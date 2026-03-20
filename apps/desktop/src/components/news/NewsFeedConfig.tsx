import { useState, useEffect, useCallback } from 'react';
import { liveFeed } from '@/services/api';
import type { NewsFeedConfig } from '@/types/livefeed';

const MAX_FEEDS = 25;

const EMPTY_FEED: NewsFeedConfig = { name: '', url: '', weight: 3 };

// ---------------------------------------------------------------------------
// Weight dots
// ---------------------------------------------------------------------------

function WeightSelector({
  value,
  onChange,
}: {
  value: number;
  onChange: (w: number) => void;
}) {
  return (
    <div className="flex items-center gap-1" title={`Weight: ${value}/5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={`h-2.5 w-2.5 rounded-full transition-colors ${
            n <= value
              ? 'bg-blue-500 hover:bg-blue-400'
              : 'bg-zinc-600 hover:bg-zinc-500'
          }`}
          aria-label={`Set weight to ${n}`}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function NewsFeedConfigPanel() {
  const [feeds, setFeeds] = useState<NewsFeedConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  // ---- Load feeds on mount ------------------------------------------------

  const loadFeeds = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = (await liveFeed.getFeeds()) as NewsFeedConfig[];
      setFeeds(data);
      setDirty(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load feeds';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFeeds();
  }, [loadFeeds]);

  // ---- Handlers -----------------------------------------------------------

  const updateFeed = (index: number, patch: Partial<NewsFeedConfig>) => {
    setFeeds((prev) => prev.map((f, i) => (i === index ? { ...f, ...patch } : f)));
    setDirty(true);
  };

  const removeFeed = (index: number) => {
    setFeeds((prev) => prev.filter((_, i) => i !== index));
    setDirty(true);
  };

  const addFeed = () => {
    if (feeds.length >= MAX_FEEDS) return;
    setFeeds((prev) => [...prev, { ...EMPTY_FEED }]);
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await liveFeed.updateFeeds(feeds);
      setDirty(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save feeds';
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    setError(null);
    try {
      await liveFeed.resetFeeds();
      await loadFeeds();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reset feeds';
      setError(msg);
      setLoading(false);
    }
  };

  // ---- Render -------------------------------------------------------------

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-900">
        <div className="flex items-center gap-2 text-sm text-zinc-400">
          <svg
            className="h-4 w-4 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
          Loading feed configuration...
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-700 bg-zinc-900 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-200">
          RSS Feed Configuration
        </h3>
        <span className="text-xs text-zinc-500">
          {feeds.length}/{MAX_FEEDS} feeds maximum
        </span>
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Feed list */}
      <div className="flex max-h-[420px] flex-col gap-2 overflow-y-auto pr-1">
        {feeds.length === 0 && (
          <p className="py-6 text-center text-xs text-zinc-500">
            No feeds configured. Click &quot;Add Feed&quot; to get started.
          </p>
        )}

        {feeds.map((feed, idx) => (
          <div
            key={idx}
            className="group flex items-start gap-2 rounded border border-zinc-700/60 bg-zinc-800/60 px-3 py-2"
          >
            {/* Index label */}
            <span className="mt-1.5 min-w-[1.25rem] text-right text-[10px] tabular-nums text-zinc-500">
              {idx + 1}.
            </span>

            {/* Inputs */}
            <div className="flex min-w-0 flex-1 flex-col gap-1.5">
              <input
                type="text"
                value={feed.name}
                onChange={(e) => updateFeed(idx, { name: e.target.value })}
                placeholder="Feed name"
                className="w-full rounded bg-zinc-900 px-2 py-1 text-xs text-zinc-200 placeholder-zinc-600 outline-none ring-1 ring-zinc-700 focus:ring-blue-500/60"
              />
              <input
                type="text"
                value={feed.url}
                onChange={(e) => updateFeed(idx, { url: e.target.value })}
                placeholder="https://example.com/rss.xml"
                className="w-full rounded bg-zinc-900 px-2 py-1 text-xs text-zinc-300 placeholder-zinc-600 outline-none ring-1 ring-zinc-700 focus:ring-blue-500/60"
              />
            </div>

            {/* Weight */}
            <div className="mt-1.5 flex flex-col items-center gap-0.5">
              <WeightSelector
                value={feed.weight}
                onChange={(w) => updateFeed(idx, { weight: w })}
              />
              <span className="text-[9px] text-zinc-500">weight</span>
            </div>

            {/* Remove button */}
            <button
              type="button"
              onClick={() => removeFeed(idx)}
              className="mt-1 rounded p-1 text-zinc-500 transition-colors hover:bg-red-500/15 hover:text-red-400"
              title="Remove feed"
            >
              <svg
                className="h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        ))}
      </div>

      {/* Action bar */}
      <div className="flex items-center gap-2 border-t border-zinc-700/60 pt-3">
        <button
          type="button"
          onClick={addFeed}
          disabled={feeds.length >= MAX_FEEDS}
          className="rounded bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          + Add Feed
        </button>

        <button
          type="button"
          onClick={handleReset}
          className="rounded bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-700"
        >
          Reset to Defaults
        </button>

        <div className="flex-1" />

        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !dirty}
          className="rounded bg-blue-600 px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </div>
  );
}
