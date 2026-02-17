import { useState } from 'react';
import { Bell, MapPin, BarChart3, Settings as SettingsIcon } from 'lucide-react';
import AlertFeed from './AlertFeed';
import ZoneManager from './ZoneManager';
import AnalyticsDash from './AnalyticsDash';
import Settings from './Settings';

const TABS = [
  { key: 'alerts', label: 'Alerts', icon: Bell },
  { key: 'zones', label: 'Zones', icon: MapPin },
  { key: 'analytics', label: 'Analytics', icon: BarChart3 },
  { key: 'settings', label: 'Settings', icon: SettingsIcon },
];

export default function ControlPanel({
  alerts,
  zones,
  analytics,
  settings,
  onSettingsChange,
  onAddZone,
  onDeleteZone,
  onToggleDrawing,
  isDrawing,
}) {
  const [activeTab, setActiveTab] = useState('alerts');

  const alertCount = alerts?.length || 0;
  const zoneCount = zones?.length || 0;

  function getBadge(key) {
    if (key === 'alerts' && alertCount > 0) return alertCount;
    if (key === 'zones' && zoneCount > 0) return zoneCount;
    return null;
  }

  return (
    <div className="flex flex-col h-full card m-2 ml-0 overflow-hidden">
      {/* Tab bar */}
      <div className="flex border-b border-slate-700/50">
        {TABS.map(({ key, label, icon: Icon }) => {
          const badge = getBadge(key);
          return (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 text-xs font-medium transition-colors relative ${
                activeTab === key ? 'tab-active' : 'tab-inactive'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{label}</span>
              {badge != null && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 flex items-center justify-center rounded-full bg-safety-orange text-[9px] font-bold text-white px-1 font-data">
                  {badge > 99 ? '99+' : badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'alerts' && <AlertFeed alerts={alerts} />}
        {activeTab === 'zones' && (
          <ZoneManager
            zones={zones}
            onAddZone={onAddZone}
            onDeleteZone={onDeleteZone}
            onToggleDrawing={onToggleDrawing}
            isDrawing={isDrawing}
          />
        )}
        {activeTab === 'analytics' && <AnalyticsDash analytics={analytics} />}
        {activeTab === 'settings' && (
          <Settings settings={settings} onSave={onSettingsChange} />
        )}
      </div>
    </div>
  );
}
