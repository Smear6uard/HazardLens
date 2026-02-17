import { useEffect, useRef, useState, useCallback } from 'react';
import { Bell, AlertTriangle, Info, Filter } from 'lucide-react';
import { SEVERITY_COLORS } from '../utils/constants';

function playAlertSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.setValueAtTime(660, ctx.currentTime + 0.1);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.3);
  } catch {
    // Audio not available
  }
}

const SEVERITY_ICON = {
  critical: AlertTriangle,
  warning: Bell,
  info: Info,
};

export default function AlertFeed({ alerts = [] }) {
  const scrollRef = useRef(null);
  const [filter, setFilter] = useState('all');
  const prevCountRef = useRef(0);

  // Sound on new critical alerts
  useEffect(() => {
    const criticalCount = alerts.filter((a) => a.severity === 'critical').length;
    if (criticalCount > prevCountRef.current && prevCountRef.current > 0) {
      playAlertSound();
    }
    prevCountRef.current = criticalCount;
  }, [alerts]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [alerts.length]);

  const filtered = filter === 'all' ? alerts : alerts.filter((a) => a.severity === filter);

  const formatTime = useCallback((ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-slate-700/50">
        <Filter className="w-3.5 h-3.5 text-slate-500" />
        {['all', 'critical', 'warning', 'info'].map((sev) => (
          <button
            key={sev}
            onClick={() => setFilter(sev)}
            className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
              filter === sev
                ? sev === 'all'
                  ? 'bg-slate-600 text-white'
                  : `${SEVERITY_COLORS[sev].bg} ${SEVERITY_COLORS[sev].text}`
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {sev.charAt(0).toUpperCase() + sev.slice(1)}
            {sev !== 'all' && (
              <span className="ml-1 font-data">
                {alerts.filter((a) => a.severity === sev).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-slate-500">
            <Bell className="w-6 h-6 mb-1" />
            <span className="text-xs">No alerts yet</span>
          </div>
        ) : (
          filtered.map((alert, i) => {
            const sev = SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.info;
            const Icon = SEVERITY_ICON[alert.severity] || Info;
            return (
              <div
                key={alert.id || i}
                className={`animate-slide-in flex items-start gap-2 p-2.5 rounded-lg border-l-3 ${sev.bg} ${sev.border} border-l-[3px]`}
              >
                <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${sev.text}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-xs font-semibold ${sev.text}`}>
                      {(alert.event_type || alert.type || '').replace(/_/g, ' ').toUpperCase()}
                    </span>
                    <span className="text-[10px] font-data text-slate-500 flex-shrink-0">
                      {formatTime(alert.timestamp)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-0.5 leading-snug">
                    {alert.description || alert.message || 'Safety event detected'}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
