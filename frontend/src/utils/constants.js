export const API_BASE = '/api';

export const SEVERITY_COLORS = {
  critical: { bg: 'bg-red-500/20', border: 'border-red-500', text: 'text-red-400', dot: 'bg-red-500' },
  warning:  { bg: 'bg-orange-500/20', border: 'border-orange-500', text: 'text-orange-400', dot: 'bg-orange-500' },
  info:     { bg: 'bg-yellow-500/20', border: 'border-yellow-500', text: 'text-yellow-400', dot: 'bg-yellow-500' },
};

export const ZONE_TYPES = [
  { value: 'restricted', label: 'Restricted Area', color: '#ef4444' },
  { value: 'hazard', label: 'Hazard Zone', color: '#f97316' },
  { value: 'ppe_required', label: 'PPE Required', color: '#eab308' },
];

export const DEFAULT_SETTINGS = {
  confidence_threshold: 0.5,
  target_fps: 6,
  proximity_threshold: 50,
  loiter_time: 30,
  enable_ppe: true,
  enable_zones: true,
  enable_nearmiss: true,
  enable_fallen: true,
};

export const RISK_LEVELS = [
  { max: 25, label: 'Low', color: '#22c55e' },
  { max: 50, label: 'Medium', color: '#eab308' },
  { max: 75, label: 'High', color: '#f97316' },
  { max: 100, label: 'Critical', color: '#ef4444' },
];

export const EVENT_TYPES = [
  'no_hardhat',
  'no_vest',
  'zone_violation',
  'near_miss',
  'fallen_person',
  'proximity_alert',
];
