import { useMemo } from 'react';
import { RISK_LEVELS } from '../utils/constants';

export default function RiskGauge({ score = 0 }) {
  const clamped = Math.max(0, Math.min(100, score));

  const { label, color } = useMemo(() => {
    for (const level of RISK_LEVELS) {
      if (clamped <= level.max) return level;
    }
    return RISK_LEVELS[RISK_LEVELS.length - 1];
  }, [clamped]);

  // SVG semicircle gauge
  const radius = 80;
  const cx = 100;
  const cy = 95;
  const circumference = Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  // Needle angle: -180 (left) to 0 (right)
  const needleAngle = -180 + (clamped / 100) * 180;

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 120" className="w-full max-w-[240px]">
        <defs>
          <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22c55e" />
            <stop offset="40%" stopColor="#eab308" />
            <stop offset="70%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>

        {/* Background arc */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="#334155"
          strokeWidth="12"
          strokeLinecap="round"
        />

        {/* Filled arc */}
        <path
          d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
          fill="none"
          stroke="url(#gaugeGradient)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="animate-gauge-fill"
          style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
        />

        {/* Needle */}
        <g transform={`rotate(${needleAngle}, ${cx}, ${cy})`} style={{ transition: 'transform 0.8s ease-out' }}>
          <line
            x1={cx}
            y1={cy}
            x2={cx - radius + 18}
            y2={cy}
            stroke={color}
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <circle cx={cx} cy={cy} r="5" fill={color} />
        </g>

        {/* Score text */}
        <text
          x={cx}
          y={cy - 20}
          textAnchor="middle"
          className="font-data"
          fill="white"
          fontSize="28"
          fontWeight="700"
        >
          {Math.round(clamped)}
        </text>

        {/* Label */}
        <text
          x={cx}
          y={cy - 2}
          textAnchor="middle"
          fill={color}
          fontSize="12"
          fontWeight="600"
        >
          {label}
        </text>
      </svg>
      <span className="text-xs text-slate-500 -mt-1">Risk Score</span>
    </div>
  );
}
