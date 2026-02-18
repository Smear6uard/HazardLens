import { useState } from 'react';
import { MapPin, Plus, Trash2 } from 'lucide-react';
import { ZONE_TYPES } from '../utils/constants';
import { deleteZone as apiDeleteZone } from '../utils/api';

export default function ZoneManager({ zones = [], onDeleteZone, onToggleDrawing, isDrawing }) {
  const [deleting, setDeleting] = useState(null);

  async function handleDelete(zoneId) {
    setDeleting(zoneId);
    try {
      await apiDeleteZone(zoneId);
    } catch {
      // Backend may have already removed it, or ID mismatch — continue anyway
    }
    // Always remove from frontend regardless of API result
    onDeleteZone?.(zoneId);
    setDeleting(null);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-700/50">
        <span className="text-sm font-medium text-slate-300">
          Safety Zones ({zones.length})
        </span>
        <button
          onClick={onToggleDrawing}
          className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
            isDrawing
              ? 'bg-safety-orange text-white'
              : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
          }`}
        >
          <Plus className="w-3 h-3" />
          {isDrawing ? 'Drawing...' : 'Add Zone'}
        </button>
      </div>

      {/* Zone list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {zones.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-slate-500">
            <MapPin className="w-6 h-6 mb-1" />
            <span className="text-xs">No zones defined</span>
            <span className="text-[10px] text-slate-600 mt-0.5">
              Click "Add Zone" to draw one
            </span>
          </div>
        ) : (
          zones.map((zone) => {
            const typeInfo = ZONE_TYPES.find((t) => t.value === (zone.type || zone.zone_type)) || ZONE_TYPES[0];
            return (
              <div
                key={zone.id}
                className="flex items-center gap-3 p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/30"
              >
                <div
                  className="w-3 h-3 rounded-sm flex-shrink-0"
                  style={{ backgroundColor: typeInfo.color }}
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-200 truncate">
                    {zone.name || typeInfo.label}
                  </div>
                  <div className="text-[10px] text-slate-500 font-data">
                    {typeInfo.label} &middot; {zone.vertices?.length || 0} vertices
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleDelete(zone.id)}
                    disabled={deleting === zone.id}
                    className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Delete zone"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
