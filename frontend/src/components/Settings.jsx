import { useState, useEffect } from 'react';
import { Save, RotateCcw } from 'lucide-react';
import { DEFAULT_SETTINGS } from '../utils/constants';
import { updateSettings } from '../utils/api';

function Slider({ label, value, onChange, min, max, step = 1, unit = '' }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <label className="text-xs text-slate-400">{label}</label>
        <span className="text-xs font-data text-slate-300">
          {value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-safety-orange"
      />
    </div>
  );
}

function Toggle({ label, description, checked, onChange }) {
  return (
    <div className="flex items-center justify-between py-1">
      <div>
        <span className="text-sm text-slate-300">{label}</span>
        {description && (
          <p className="text-[10px] text-slate-500">{description}</p>
        )}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative w-9 h-5 rounded-full transition-colors ${
          checked ? 'bg-safety-orange' : 'bg-slate-600'
        }`}
      >
        <span
          className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
            checked ? 'left-[18px]' : 'left-0.5'
          }`}
        />
      </button>
    </div>
  );
}

export default function Settings({ settings: initialSettings, onSave }) {
  const [settings, setSettings] = useState(initialSettings || DEFAULT_SETTINGS);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (initialSettings) setSettings(initialSettings);
  }, [initialSettings]);

  function update(key, value) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    try {
      await updateSettings(settings);
      onSave?.(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // save failed silently
    } finally {
      setSaving(false);
    }
  }

  function handleReset() {
    setSettings(DEFAULT_SETTINGS);
    setSaved(false);
  }

  return (
    <div className="flex flex-col gap-4 p-3 overflow-y-auto h-full">
      {/* Detection thresholds */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
          Detection Thresholds
        </h3>
        <div className="space-y-4">
          <Slider
            label="Confidence Threshold"
            value={settings.confidence_threshold}
            onChange={(v) => update('confidence_threshold', v)}
            min={0.1}
            max={0.9}
            step={0.05}
          />
          <Slider
            label="Target FPS"
            value={settings.target_fps}
            onChange={(v) => update('target_fps', v)}
            min={1}
            max={30}
            step={1}
            unit=" fps"
          />
          <Slider
            label="Proximity Threshold"
            value={settings.proximity_threshold}
            onChange={(v) => update('proximity_threshold', v)}
            min={10}
            max={200}
            step={5}
            unit=" px"
          />
          <Slider
            label="Loiter Time"
            value={settings.loiter_time}
            onChange={(v) => update('loiter_time', v)}
            min={5}
            max={120}
            step={5}
            unit=" sec"
          />
        </div>
      </div>

      {/* Detection features */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
          Detection Features
        </h3>
        <div className="space-y-2">
          <Toggle
            label="PPE Detection"
            description="Detect hardhats, vests, gloves"
            checked={settings.enable_ppe}
            onChange={(v) => update('enable_ppe', v)}
          />
          <Toggle
            label="Zone Monitoring"
            description="Restricted area violations"
            checked={settings.enable_zones}
            onChange={(v) => update('enable_zones', v)}
          />
          <Toggle
            label="Near-Miss Detection"
            description="Proximity alerts between workers & equipment"
            checked={settings.enable_nearmiss}
            onChange={(v) => update('enable_nearmiss', v)}
          />
          <Toggle
            label="Fallen Person"
            description="Detect fallen or motionless workers"
            checked={settings.enable_fallen}
            onChange={(v) => update('enable_fallen', v)}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-slate-700/50">
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary flex items-center gap-1.5 text-sm flex-1 justify-center"
        >
          <Save className="w-3.5 h-3.5" />
          {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Settings'}
        </button>
        <button
          onClick={handleReset}
          className="btn-secondary flex items-center gap-1.5 text-sm"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset
        </button>
      </div>
    </div>
  );
}
