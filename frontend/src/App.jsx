import { useState, useCallback, useEffect } from 'react';
import Header from './components/Header';
import VideoPanel from './components/VideoPanel';
import ControlPanel from './components/ControlPanel';
import useSSE from './utils/useSSE';
import useWebSocket from './utils/useWebSocket';
import { DEFAULT_SETTINGS } from './utils/constants';
import {
  uploadVideo,
  getStreamUrl,
  getDemoStreamUrl,
  getWebSocketUrl,
  getZones,
  createZone,
  getDemoAnalytics,
  getAnalytics,
} from './utils/api';

export default function App() {
  // Core state
  const [mode, setMode] = useState('demo');
  const [jobId, setJobId] = useState(null);
  const [zones, setZones] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [isDrawing, setIsDrawing] = useState(false);
  const [error, setError] = useState(null);

  // Compute stream URL based on mode
  const sseUrl =
    mode === 'demo'
      ? getDemoStreamUrl()
      : mode === 'upload' && jobId
      ? getStreamUrl(jobId)
      : null;

  const wsEnabled = mode === 'webcam';

  // SSE hook for demo and upload modes
  const {
    frame: sseFrame,
    alerts: sseAlerts,
    isStreaming: sseStreaming,
    stats: sseStats,
    error: sseError,
  } = useSSE(sseUrl);

  // WebSocket hook for webcam mode
  const {
    frame: wsFrame,
    alerts: wsAlerts,
    isConnected: wsConnected,
    sendFrame: wsSendFrame,
    error: wsError,
  } = useWebSocket(getWebSocketUrl(), wsEnabled);

  // Derived values based on mode
  const frame = mode === 'webcam' ? wsFrame : sseFrame;
  const alerts = mode === 'webcam' ? wsAlerts : sseAlerts;
  const isStreaming = mode === 'webcam' ? wsConnected : sseStreaming;
  const stats = sseStats;

  // Load initial data
  useEffect(() => {
    async function loadInitial() {
      try {
        const zonesData = await getZones();
        setZones(zonesData);
      } catch {
        // API not available yet
      }
    }
    loadInitial();
  }, []);

  // Poll analytics
  useEffect(() => {
    let mounted = true;
    async function fetchAnalytics() {
      try {
        const data =
          mode === 'demo'
            ? await getDemoAnalytics()
            : jobId
            ? await getAnalytics(jobId)
            : null;
        if (mounted && data) setAnalytics(data);
      } catch {
        // skip
      }
    }

    if (isStreaming || mode === 'demo') {
      fetchAnalytics();
      const id = setInterval(fetchAnalytics, 3000);
      return () => {
        mounted = false;
        clearInterval(id);
      };
    }
    return () => { mounted = false; };
  }, [mode, jobId, isStreaming]);

  // Handle file upload
  const handleFileSelect = useCallback(async (file) => {
    setError(null);
    try {
      const result = await uploadVideo(file);
      setJobId(result.job_id);
      setMode('upload');
    } catch (err) {
      setError(err.message);
    }
  }, []);

  // Handle mode change
  const handleModeChange = useCallback((newMode) => {
    setMode(newMode);
    setError(null);
    if (newMode !== 'upload') setJobId(null);
  }, []);

  // Handle webcam frame
  const handleWebcamFrame = useCallback(
    (base64) => {
      wsSendFrame(base64);
    },
    [wsSendFrame]
  );

  // Zone management
  const handleZoneComplete = useCallback(async (zoneData) => {
    setIsDrawing(false);
    try {
      // Map frontend format {type, vertices: [{x,y}]} to backend {zone_type, polygon: [[x,y]]}
      const payload = {
        name: `Zone ${Date.now().toString(36).slice(-4).toUpperCase()}`,
        zone_type: zoneData.type,
        polygon: zoneData.vertices.map((v) => [v.x, v.y]),
      };
      await createZone(payload);
      // Store in frontend format for rendering
      setZones((prev) => [...prev, { ...payload, id: payload.name, vertices: zoneData.vertices, type: zoneData.type }]);
    } catch {
      // zone creation failed
    }
  }, []);

  const handleDeleteZone = useCallback((zoneId) => {
    setZones((prev) => prev.filter((z) => z.id !== zoneId));
  }, []);

  const handleSettingsChange = useCallback((newSettings) => {
    setSettings(newSettings);
  }, []);

  const currentError = error || sseError || wsError;

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header
        mode={mode}
        onModeChange={handleModeChange}
        onFileSelect={handleFileSelect}
      />

      {/* Error banner */}
      {currentError && (
        <div className="mx-2 mt-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs flex items-center justify-between">
          <span>{currentError}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-300 text-xs ml-2"
          >
            dismiss
          </button>
        </div>
      )}

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden flex-col lg:flex-row">
        {/* Video panel — 60% on desktop */}
        <div className="lg:w-[60%] w-full flex-shrink-0">
          <VideoPanel
            mode={mode}
            frame={frame}
            isStreaming={isStreaming}
            stats={stats}
            onFileSelect={handleFileSelect}
            webcamEnabled={wsEnabled}
            onWebcamFrame={handleWebcamFrame}
            zones={zones}
            drawingZone={isDrawing}
            onZoneComplete={handleZoneComplete}
          />
        </div>

        {/* Control panel — 40% on desktop */}
        <div className="lg:w-[40%] w-full flex-1 min-h-0">
          <ControlPanel
            alerts={alerts}
            zones={zones}
            analytics={analytics}
            settings={settings}
            onSettingsChange={handleSettingsChange}
            onAddZone={() => setIsDrawing(true)}
            onDeleteZone={handleDeleteZone}
            onToggleDrawing={() => setIsDrawing((p) => !p)}
            isDrawing={isDrawing}
          />
        </div>
      </div>
    </div>
  );
}
