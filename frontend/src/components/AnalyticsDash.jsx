import { useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { Users, ShieldCheck, AlertTriangle, Activity } from 'lucide-react';
import RiskGauge from './RiskGauge';

const PIE_COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6'];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="font-data">
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
        </p>
      ))}
    </div>
  );
};

function StatCard({ icon: Icon, label, value, color = 'text-white', sub }) {
  return (
    <div className="stat-card">
      <div className="flex items-center gap-2">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-[10px] uppercase tracking-wide text-slate-500">{label}</span>
      </div>
      <span className={`text-xl font-bold font-data ${color}`}>{value}</span>
      {sub && <span className="text-[10px] text-slate-500">{sub}</span>}
    </div>
  );
}

export default function AnalyticsDash({ analytics }) {
  const data = analytics || {};

  // Map backend Analytics model field names to display values
  // Prefer per-frame risk_score (current) over avg_risk_score (diluted average)
  const riskScore = data.risk_score ?? data.avg_risk_score ?? 0;
  const compliancePercent = (data.compliance_rate ?? 1.0) * 100;
  const totalEvents = data.total_events ?? 0;
  const criticalEvents = data.critical_events ?? 0;

  const complianceData = useMemo(() => {
    if (!data.compliance_over_time?.length) return [];
    // Backend sends list of {timestamp, value} TimeSeriesPoint objects
    return data.compliance_over_time.map((pt, i) => ({
      time: `${i}`,
      value: (typeof pt === 'object' ? pt.value : pt) * 100,
    }));
  }, [data.compliance_over_time]);

  const alertsPerMinute = useMemo(() => {
    if (!data.alerts_per_minute?.length) return [];
    // Backend sends list of {timestamp, value} TimeSeriesPoint objects
    return data.alerts_per_minute.map((pt, i) => ({
      time: `${i}m`,
      count: typeof pt === 'object' ? pt.value : pt,
    }));
  }, [data.alerts_per_minute]);

  const eventDist = useMemo(() => {
    // Backend field is event_type_counts (dict), not event_distribution
    const counts = data.event_type_counts || data.event_distribution || {};
    return Object.entries(counts).map(([name, value]) => ({
      name: name.replace(/_/g, ' '),
      value,
    }));
  }, [data.event_type_counts, data.event_distribution]);

  return (
    <div className="flex flex-col gap-3 p-3 overflow-y-auto h-full">
      {/* Stat cards row */}
      <div className="grid grid-cols-2 gap-2">
        <StatCard
          icon={Users}
          label="Total Events"
          value={analytics ? totalEvents : '--'}
          color="text-blue-400"
        />
        <StatCard
          icon={ShieldCheck}
          label="PPE Compliance"
          value={analytics ? `${Math.round(compliancePercent)}%` : '--'}
          color="text-safety-green"
        />
        <StatCard
          icon={AlertTriangle}
          label="Critical Alerts"
          value={analytics ? criticalEvents : '--'}
          color="text-safety-orange"
          sub={totalEvents > 0 ? `of ${totalEvents} total` : undefined}
        />
        <StatCard
          icon={Activity}
          label="Risk Score"
          value={analytics ? Math.round(riskScore) : '--'}
          color={
            riskScore > 75
              ? 'text-red-400'
              : riskScore > 50
              ? 'text-safety-orange'
              : riskScore > 0
              ? 'text-safety-green'
              : 'text-white'
          }
        />
      </div>

      {/* Risk gauge */}
      <div className="card p-4">
        <RiskGauge score={riskScore} />
      </div>

      {/* Compliance over time */}
      {complianceData.length > 0 && (
        <div className="card p-3">
          <h3 className="text-xs font-semibold text-slate-400 mb-2">PPE Compliance Over Time</h3>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={complianceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#64748b' }} />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#22c55e"
                strokeWidth={2}
                dot={false}
                name="Compliance %"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Alerts per minute */}
      {alertsPerMinute.length > 0 && (
        <div className="card p-3">
          <h3 className="text-xs font-semibold text-slate-400 mb-2">Alerts per Minute</h3>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={alertsPerMinute}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" fill="#f97316" radius={[3, 3, 0, 0]} name="Alerts" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Event distribution pie */}
      {eventDist.length > 0 && (
        <div className="card p-3">
          <h3 className="text-xs font-semibold text-slate-400 mb-2">Event Distribution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={eventDist}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={55}
                innerRadius={30}
                paddingAngle={3}
                label={({ name, percent }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
                labelLine={{ stroke: '#64748b', strokeWidth: 1 }}
              >
                {eventDist.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
