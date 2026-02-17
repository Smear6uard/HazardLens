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

  const complianceData = useMemo(() => {
    if (!data.compliance_over_time) return [];
    return data.compliance_over_time.map((v, i) => ({ time: `${i}s`, value: v }));
  }, [data.compliance_over_time]);

  const alertsPerMinute = useMemo(() => {
    if (!data.alerts_per_minute) return [];
    return data.alerts_per_minute.map((v, i) => ({ time: `${i}m`, count: v }));
  }, [data.alerts_per_minute]);

  const eventDist = useMemo(() => {
    if (!data.event_distribution) return [];
    return Object.entries(data.event_distribution).map(([name, value]) => ({
      name: name.replace(/_/g, ' '),
      value,
    }));
  }, [data.event_distribution]);

  return (
    <div className="flex flex-col gap-3 p-3 overflow-y-auto h-full">
      {/* Stat cards row */}
      <div className="grid grid-cols-2 gap-2">
        <StatCard
          icon={Users}
          label="Workers"
          value={data.total_workers ?? '--'}
          color="text-blue-400"
        />
        <StatCard
          icon={ShieldCheck}
          label="PPE Compliance"
          value={data.ppe_compliance != null ? `${Math.round(data.ppe_compliance)}%` : '--'}
          color="text-safety-green"
        />
        <StatCard
          icon={AlertTriangle}
          label="Active Alerts"
          value={data.active_alerts ?? '--'}
          color="text-safety-orange"
        />
        <StatCard
          icon={Activity}
          label="Risk Score"
          value={data.risk_score != null ? Math.round(data.risk_score) : '--'}
          color={
            (data.risk_score ?? 0) > 75
              ? 'text-red-400'
              : (data.risk_score ?? 0) > 50
              ? 'text-safety-orange'
              : 'text-safety-green'
          }
        />
      </div>

      {/* Risk gauge */}
      <div className="card p-4">
        <RiskGauge score={data.risk_score ?? 0} />
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
          <ResponsiveContainer width="100%" height={160}>
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
