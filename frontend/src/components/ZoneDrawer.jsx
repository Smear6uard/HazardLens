import { useRef, useState, useCallback, useEffect } from 'react';
import { ZONE_TYPES } from '../utils/constants';

export default function ZoneDrawer({ zones = [], isDrawing, onZoneComplete }) {
  const canvasRef = useRef(null);
  const [vertices, setVertices] = useState([]);
  const [mousePos, setMousePos] = useState(null);
  const [zoneType, setZoneType] = useState('restricted');

  const getCanvasPoint = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / rect.width,
      y: (e.clientY - rect.top) / rect.height,
    };
  }, []);

  const handleClick = useCallback(
    (e) => {
      if (!isDrawing) return;
      const pt = getCanvasPoint(e);
      if (!pt) return;

      // Close polygon if clicking near first vertex
      if (vertices.length >= 3) {
        const first = vertices[0];
        const dist = Math.sqrt((pt.x - first.x) ** 2 + (pt.y - first.y) ** 2);
        if (dist < 0.03) {
          onZoneComplete?.({ type: zoneType, vertices });
          setVertices([]);
          return;
        }
      }

      setVertices((prev) => [...prev, pt]);
    },
    [isDrawing, vertices, zoneType, getCanvasPoint, onZoneComplete]
  );

  const handleDoubleClick = useCallback(
    (e) => {
      e.preventDefault();
      if (!isDrawing || vertices.length < 3) return;
      onZoneComplete?.({ type: zoneType, vertices });
      setVertices([]);
    },
    [isDrawing, vertices, zoneType, onZoneComplete]
  );

  const handleMouseMove = useCallback(
    (e) => {
      if (!isDrawing) return;
      setMousePos(getCanvasPoint(e));
    },
    [isDrawing, getCanvasPoint]
  );

  // Draw on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);

    // Draw existing zones
    for (const zone of zones) {
      if (!zone.vertices || zone.vertices.length < 3) continue;
      const typeInfo = ZONE_TYPES.find((t) => t.value === zone.type) || ZONE_TYPES[0];
      ctx.beginPath();
      ctx.moveTo(zone.vertices[0].x * width, zone.vertices[0].y * height);
      for (let i = 1; i < zone.vertices.length; i++) {
        ctx.lineTo(zone.vertices[i].x * width, zone.vertices[i].y * height);
      }
      ctx.closePath();
      ctx.fillStyle = typeInfo.color + '20';
      ctx.fill();
      ctx.strokeStyle = typeInfo.color;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Label
      const cx = zone.vertices.reduce((s, v) => s + v.x, 0) / zone.vertices.length * width;
      const cy = zone.vertices.reduce((s, v) => s + v.y, 0) / zone.vertices.length * height;
      ctx.font = '11px Inter, sans-serif';
      ctx.fillStyle = typeInfo.color;
      ctx.textAlign = 'center';
      ctx.fillText(zone.name || typeInfo.label, cx, cy);
    }

    // Draw in-progress polygon
    if (vertices.length > 0) {
      const typeInfo = ZONE_TYPES.find((t) => t.value === zoneType) || ZONE_TYPES[0];
      ctx.beginPath();
      ctx.moveTo(vertices[0].x * width, vertices[0].y * height);
      for (let i = 1; i < vertices.length; i++) {
        ctx.lineTo(vertices[i].x * width, vertices[i].y * height);
      }
      if (mousePos) {
        ctx.lineTo(mousePos.x * width, mousePos.y * height);
      }
      ctx.strokeStyle = typeInfo.color;
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 3]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw vertices
      for (const v of vertices) {
        ctx.beginPath();
        ctx.arc(v.x * width, v.y * height, 4, 0, Math.PI * 2);
        ctx.fillStyle = typeInfo.color;
        ctx.fill();
      }

      // Highlight first vertex (close target)
      if (vertices.length >= 3) {
        ctx.beginPath();
        ctx.arc(vertices[0].x * width, vertices[0].y * height, 10, 0, Math.PI * 2);
        ctx.strokeStyle = typeInfo.color + '80';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }
  }, [zones, vertices, mousePos, zoneType]);

  return (
    <>
      <canvas
        ref={canvasRef}
        width={1280}
        height={720}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        onMouseMove={handleMouseMove}
        className="absolute inset-0 w-full h-full"
        style={{ cursor: isDrawing ? 'crosshair' : 'default' }}
      />
      {isDrawing && (
        <div className="absolute bottom-3 left-3 flex items-center gap-2 bg-black/70 backdrop-blur-sm rounded-lg px-3 py-2">
          <label className="text-xs text-slate-300">Zone type:</label>
          <select
            value={zoneType}
            onChange={(e) => setZoneType(e.target.value)}
            className="input-field text-xs py-1 px-2"
          >
            {ZONE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <span className="text-xs text-slate-400 ml-2">
            {vertices.length === 0
              ? 'Click to place vertices'
              : vertices.length < 3
              ? `${vertices.length} pts — need ${3 - vertices.length} more`
              : 'Double-click or click first point to close'}
          </span>
        </div>
      )}
    </>
  );
}
