import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { useMonitoringStore, type WatchTarget, type Alert } from '@/stores/useMonitoringStore';
import { monitoring } from '@/services/api';

type MonitoringTab = 'watchlist' | 'alerts' | 'rules';

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-400/10 border-red-400/30',
  high: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
  medium: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
  low: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
  info: 'text-nexus-text-secondary bg-nexus-bg border-nexus-border',
};

const INT_TYPES = ['CYBINT', 'SOCMINT', 'SIGINT', 'GEOINT'];

const SCAN_TYPES: Record<string, string[]> = {
  CYBINT: ['full', 'host', 'search', 'dns', 'whois', 'certificates', 'ip', 'domain'],
  SOCMINT: ['keyword_search', 'user_timeline', 'user_info', 'username_search'],
  SIGINT: ['aircraft_state', 'area_aircraft', 'vessel_position', 'area_vessels'],
  GEOINT: ['satellite_search', 'osm_bbox', 'geocode_forward'],
};

function AddWatchTargetForm({ onClose }: { onClose: () => void }) {
  const addWatchTarget = useMonitoringStore((s) => s.addWatchTarget);
  const [form, setForm] = useState({
    entityName: '',
    entityType: 'IPAddress',
    intType: 'CYBINT',
    scanType: 'full',
    query: '',
    intervalHours: 24,
    autoPivot: false,
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.query.trim() || !form.entityName.trim()) return;
    setSubmitting(true);
    try {
      const result = await monitoring.createTarget({
        entity_name: form.entityName,
        entity_type: form.entityType,
        int_type: form.intType,
        scan_type: form.scanType,
        query: form.query,
        interval_hours: form.intervalHours,
        auto_pivot: form.autoPivot,
      }) as WatchTarget;
      addWatchTarget(result);
      onClose();
    } catch {
      // handled by API layer
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="p-2 border-b border-nexus-border space-y-2"
    >
      <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-cyan">New Watch Target</p>
      <input
        type="text"
        value={form.entityName}
        onChange={(e) => setForm({ ...form, entityName: e.target.value })}
        placeholder="Target name (e.g., 1.2.3.4)"
        className="w-full px-2 py-1 text-xs font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text placeholder:text-nexus-text-secondary/50 focus:border-nexus-cyan/50 focus:outline-none"
      />
      <input
        type="text"
        value={form.query}
        onChange={(e) => setForm({ ...form, query: e.target.value })}
        placeholder="Search query"
        className="w-full px-2 py-1 text-xs font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text placeholder:text-nexus-text-secondary/50 focus:border-nexus-cyan/50 focus:outline-none"
      />
      <div className="flex gap-1">
        <select
          value={form.intType}
          onChange={(e) => {
            const intType = e.target.value;
            setForm({ ...form, intType, scanType: SCAN_TYPES[intType]?.[0] || 'full' });
          }}
          className="flex-1 px-1 py-1 text-[10px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text focus:outline-none"
        >
          {INT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select
          value={form.scanType}
          onChange={(e) => setForm({ ...form, scanType: e.target.value })}
          className="flex-1 px-1 py-1 text-[10px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text focus:outline-none"
        >
          {(SCAN_TYPES[form.intType] || []).map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="flex gap-1 items-center">
        <label className="text-[10px] font-mono text-nexus-text-secondary">Interval:</label>
        <select
          value={form.intervalHours}
          onChange={(e) => setForm({ ...form, intervalHours: Number(e.target.value) })}
          className="flex-1 px-1 py-1 text-[10px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text focus:outline-none"
        >
          <option value={1}>1h</option>
          <option value={6}>6h</option>
          <option value={12}>12h</option>
          <option value={24}>24h</option>
          <option value={72}>3d</option>
          <option value={168}>7d</option>
        </select>
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            checked={form.autoPivot}
            onChange={(e) => setForm({ ...form, autoPivot: e.target.checked })}
            className="w-3 h-3 accent-cyan-500"
          />
          <span className="text-[10px] font-mono text-nexus-text-secondary">Pivot</span>
        </label>
      </div>
      <div className="flex gap-1">
        <button
          onClick={handleSubmit}
          disabled={!form.query.trim() || !form.entityName.trim() || submitting}
          className="flex-1 py-1 text-[10px] font-mono uppercase tracking-wider bg-nexus-cyan/20 text-nexus-cyan rounded border border-nexus-cyan/30 hover:bg-nexus-cyan/30 transition-colors disabled:opacity-40"
        >
          {submitting ? 'Adding...' : 'Add Target'}
        </button>
        <button
          onClick={onClose}
          className="px-3 py-1 text-[10px] font-mono text-nexus-text-secondary hover:text-nexus-text border border-nexus-border rounded transition-colors"
        >
          Cancel
        </button>
      </div>
    </motion.div>
  );
}

function WatchTargetCard({ target }: { target: WatchTarget }) {
  const removeWatchTarget = useMonitoringStore((s) => s.removeWatchTarget);
  const updateWatchTarget = useMonitoringStore((s) => s.updateWatchTarget);

  const handleToggle = async () => {
    try {
      await monitoring.updateTarget(target.id, { active: !target.active });
      updateWatchTarget(target.id, { active: !target.active });
    } catch { /* ignore */ }
  };

  const handleDelete = async () => {
    try {
      await monitoring.deleteTarget(target.id);
      removeWatchTarget(target.id);
    } catch { /* ignore */ }
  };

  const isOverdue = target.active && new Date(target.nextCollectionAt) <= new Date();

  return (
    <div className={clsx(
      'p-2 rounded border transition-colors',
      target.active
        ? 'bg-nexus-bg/50 border-nexus-border hover:border-nexus-cyan/30'
        : 'bg-nexus-bg/30 border-nexus-border/50 opacity-60'
    )}>
      <div className="flex items-start justify-between mb-1">
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-mono text-nexus-text truncate">{target.entityName}</p>
          <div className="flex items-center gap-1 mt-0.5">
            <span className="text-[8px] font-mono text-nexus-cyan bg-nexus-cyan/10 px-1 rounded">
              {target.intType}
            </span>
            <span className="text-[8px] font-mono text-nexus-text-secondary">
              {target.scanType}
            </span>
            <span className="text-[8px] font-mono text-nexus-text-secondary">
              / {target.intervalHours}h
            </span>
            {target.autoPivot && (
              <span className="text-[8px] font-mono text-emerald-400 bg-emerald-400/10 px-1 rounded">
                PIVOT
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 ml-1">
          <button
            onClick={handleToggle}
            className={clsx(
              'w-5 h-5 rounded flex items-center justify-center text-[9px] border transition-colors',
              target.active
                ? 'text-green-400 border-green-400/30 bg-green-400/10 hover:bg-green-400/20'
                : 'text-nexus-text-secondary border-nexus-border hover:border-nexus-text-secondary'
            )}
            title={target.active ? 'Pause' : 'Resume'}
          >
            {target.active ? '||' : '>'}
          </button>
          <button
            onClick={handleDelete}
            className="w-5 h-5 rounded flex items-center justify-center text-[9px] text-red-400 border border-red-400/30 bg-red-400/10 hover:bg-red-400/20 transition-colors"
            title="Remove"
          >
            x
          </button>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[8px] font-mono text-nexus-text-secondary">
        {target.lastCollectedAt && (
          <span>Last: {new Date(target.lastCollectedAt).toLocaleString()}</span>
        )}
        {isOverdue && (
          <span className="text-amber-400 animate-pulse">OVERDUE</span>
        )}
        {!isOverdue && target.active && (
          <span>Next: {new Date(target.nextCollectionAt).toLocaleString()}</span>
        )}
      </div>
    </div>
  );
}

function AlertCard({ alert }: { alert: Alert }) {
  const acknowledgeAlert = useMonitoringStore((s) => s.acknowledgeAlert);

  const handleAcknowledge = async () => {
    try {
      await monitoring.acknowledgeAlert(alert.id);
      acknowledgeAlert(alert.id);
    } catch { /* ignore */ }
  };

  return (
    <div className={clsx(
      'p-2 rounded border transition-colors',
      alert.acknowledged
        ? 'bg-nexus-bg/30 border-nexus-border/50 opacity-50'
        : SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.medium
    )}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1 mb-0.5">
            <span className="text-[8px] font-mono uppercase font-bold">
              {alert.severity}
            </span>
            <span className="text-[8px] font-mono opacity-70">
              {alert.alertType}
            </span>
          </div>
          <p className="text-[10px] font-mono truncate">{alert.title}</p>
          {alert.description && (
            <p className="text-[9px] opacity-70 mt-0.5 truncate">{alert.description}</p>
          )}
          <p className="text-[8px] opacity-50 mt-0.5">
            {new Date(alert.createdAt).toLocaleString()}
          </p>
        </div>
        {!alert.acknowledged && (
          <button
            onClick={handleAcknowledge}
            className="ml-1 px-1.5 py-0.5 text-[8px] font-mono uppercase rounded border border-current opacity-70 hover:opacity-100 transition-opacity"
            title="Acknowledge"
          >
            ACK
          </button>
        )}
      </div>
    </div>
  );
}

function AlertRulesSection() {
  const [rules, setRules] = useState<Array<{
    id: string; name: string; rule_type: string; severity: string; active: boolean;
  }>>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: '', rule_type: 'high_risk', severity: 'high', conditions: '{"min_risk_score": 7}' });

  useEffect(() => {
    monitoring.listAlertRules().then((r) => setRules(r as typeof rules)).catch(() => {});
  }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    try {
      const rule = await monitoring.createAlertRule({
        name: form.name,
        rule_type: form.rule_type,
        severity: form.severity,
        conditions: JSON.parse(form.conditions),
      }) as typeof rules[0];
      setRules([...rules, rule]);
      setShowAdd(false);
      setForm({ name: '', rule_type: 'high_risk', severity: 'high', conditions: '{"min_risk_score": 7}' });
    } catch { /* ignore */ }
  };

  const handleDelete = async (id: string) => {
    try {
      await monitoring.deleteAlertRule(id);
      setRules(rules.filter((r) => r.id !== id));
    } catch { /* ignore */ }
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between px-2 pt-2">
        <p className="text-[10px] font-mono uppercase tracking-wider text-nexus-text-secondary">
          Alert Rules ({rules.length})
        </p>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="text-[10px] font-mono text-nexus-cyan hover:text-nexus-text transition-colors"
        >
          {showAdd ? 'Cancel' : '+ Rule'}
        </button>
      </div>

      <AnimatePresence>
        {showAdd && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-2 space-y-1"
          >
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Rule name"
              className="w-full px-2 py-1 text-[10px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text focus:outline-none"
            />
            <div className="flex gap-1">
              <select
                value={form.rule_type}
                onChange={(e) => setForm({ ...form, rule_type: e.target.value })}
                className="flex-1 px-1 py-1 text-[10px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text focus:outline-none"
              >
                <option value="high_risk">High Risk</option>
                <option value="new_entity">New Entity</option>
              </select>
              <select
                value={form.severity}
                onChange={(e) => setForm({ ...form, severity: e.target.value })}
                className="flex-1 px-1 py-1 text-[10px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text focus:outline-none"
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <input
              type="text"
              value={form.conditions}
              onChange={(e) => setForm({ ...form, conditions: e.target.value })}
              placeholder='{"min_risk_score": 7}'
              className="w-full px-2 py-1 text-[10px] font-mono bg-nexus-bg border border-nexus-border rounded text-nexus-text focus:outline-none"
            />
            <button
              onClick={handleCreate}
              disabled={!form.name.trim()}
              className="w-full py-1 text-[10px] font-mono uppercase bg-nexus-cyan/20 text-nexus-cyan rounded border border-nexus-cyan/30 hover:bg-nexus-cyan/30 transition-colors disabled:opacity-40"
            >
              Create Rule
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="px-2 space-y-1">
        {rules.map((rule) => (
          <div key={rule.id} className="flex items-center justify-between p-1.5 rounded bg-nexus-bg/50 border border-nexus-border">
            <div>
              <p className="text-[10px] font-mono text-nexus-text">{rule.name}</p>
              <div className="flex items-center gap-1 mt-0.5">
                <span className="text-[8px] font-mono text-nexus-text-secondary">{rule.rule_type}</span>
                <span className={clsx('text-[8px] font-mono px-1 rounded', SEVERITY_COLORS[rule.severity]?.split(' ')[0])}>{rule.severity}</span>
              </div>
            </div>
            <button
              onClick={() => handleDelete(rule.id)}
              className="text-[9px] text-red-400 hover:text-red-300 transition-colors"
            >
              x
            </button>
          </div>
        ))}
        {rules.length === 0 && (
          <p className="text-[10px] text-nexus-text-secondary/50 italic py-2 text-center">
            No alert rules configured
          </p>
        )}
      </div>
    </div>
  );
}

export function MonitoringPanel() {
  const {
    watchTargets, setWatchTargets,
    alerts, setAlerts,
    loading, setLoading,
  } = useMonitoringStore();

  const [activeTab, setActiveTab] = useState<MonitoringTab>('watchlist');
  const [showAddTarget, setShowAddTarget] = useState(false);

  // Load data on mount
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [targets, alertsData] = await Promise.all([
          monitoring.listTargets(),
          monitoring.listAlerts({ limit: 100 }),
        ]);
        setWatchTargets(targets as WatchTarget[]);
        setAlerts(alertsData as Alert[]);
      } catch {
        // API may not be running
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [setWatchTargets, setAlerts, setLoading]);

  const unackCount = alerts.filter((a) => !a.acknowledged).length;

  return (
    <div className="h-full flex flex-col bg-nexus-bg-secondary overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-nexus-border">
        <h2 className="text-xs font-mono uppercase tracking-wider text-nexus-cyan">
          Monitoring Center
        </h2>
        <p className="text-[10px] font-mono text-nexus-text-secondary mt-0.5">
          {watchTargets.filter((t) => t.active).length} active targets
          {unackCount > 0 && (
            <span className="text-amber-400 ml-2">{unackCount} unacknowledged alerts</span>
          )}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-nexus-border">
        {(
          [
            { id: 'watchlist' as const, label: 'Watch List', count: watchTargets.length },
            { id: 'alerts' as const, label: 'Alerts', count: unackCount || undefined },
            { id: 'rules' as const, label: 'Rules' },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex-1 px-2 py-1.5 text-[11px] font-medium transition-colors relative',
              activeTab === tab.id
                ? 'text-nexus-cyan border-b border-nexus-cyan'
                : 'text-nexus-text-secondary hover:text-nexus-text',
            )}
          >
            {tab.label}
            {'count' in tab && tab.count != null && tab.count > 0 && (
              <span className={clsx(
                'ml-1 text-[8px] px-1 rounded-full',
                tab.id === 'alerts' ? 'bg-red-400/20 text-red-400' : 'bg-nexus-cyan/20 text-nexus-cyan'
              )}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-nexus-cyan/30 border-t-nexus-cyan rounded-full animate-spin" />
          </div>
        )}

        {!loading && activeTab === 'watchlist' && (
          <div>
            {/* Add Target Button */}
            <div className="p-2 border-b border-nexus-border">
              <button
                onClick={() => setShowAddTarget(!showAddTarget)}
                className="w-full py-1.5 text-[10px] font-mono uppercase tracking-wider border border-dashed border-nexus-cyan/30 text-nexus-cyan/70 rounded hover:bg-nexus-cyan/10 hover:text-nexus-cyan transition-colors"
              >
                {showAddTarget ? 'Cancel' : '+ Add Watch Target'}
              </button>
            </div>

            <AnimatePresence>
              {showAddTarget && (
                <AddWatchTargetForm onClose={() => setShowAddTarget(false)} />
              )}
            </AnimatePresence>

            {/* Target List */}
            <div className="p-2 space-y-1.5">
              {watchTargets.map((target) => (
                <WatchTargetCard key={target.id} target={target} />
              ))}
              {watchTargets.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-[10px] font-mono text-nexus-text-secondary/50">
                    No watch targets configured
                  </p>
                  <p className="text-[9px] font-mono text-nexus-text-secondary/30 mt-1">
                    Add targets to continuously monitor entities
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {!loading && activeTab === 'alerts' && (
          <div className="p-2 space-y-1.5">
            {alerts.length > 0 && (
              <div className="flex justify-end mb-1">
                <button
                  onClick={() => {
                    const sorted = [...alerts].sort((a, b) => {
                      if (a.acknowledged && !b.acknowledged) return 1;
                      if (!a.acknowledged && b.acknowledged) return -1;
                      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
                    });
                    setAlerts(sorted);
                  }}
                  className="text-[9px] font-mono text-nexus-text-secondary hover:text-nexus-text transition-colors"
                >
                  Sort: Unread First
                </button>
              </div>
            )}
            {alerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} />
            ))}
            {alerts.length === 0 && (
              <div className="text-center py-8">
                <p className="text-[10px] font-mono text-nexus-text-secondary/50">
                  No alerts
                </p>
                <p className="text-[9px] font-mono text-nexus-text-secondary/30 mt-1">
                  Configure alert rules to receive notifications
                </p>
              </div>
            )}
          </div>
        )}

        {!loading && activeTab === 'rules' && (
          <AlertRulesSection />
        )}
      </div>
    </div>
  );
}
