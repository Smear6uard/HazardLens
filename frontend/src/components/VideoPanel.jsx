import { useRef, useCallback, useEffect, useState } from 'react';
import Webcam from 'react-webcam';
import { Video, Upload, Camera, Loader2 } from 'lucide-react';
import ZoneDrawer from './ZoneDrawer';

export default function VideoPanel({
  mode,
  frame,
  isStreaming,
  stats,
  onFileSelect,
  webcamEnabled,
  onWebcamFrame,
  zones,
  drawingZone,
  onZoneComplete,
}) {
  const webcamRef = useRef(null);
  const captureIntervalRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  // Capture webcam frames at interval
  useEffect(() => {
    if (mode === 'webcam' && webcamEnabled && onWebcamFrame) {
      captureIntervalRef.current = setInterval(() => {
        const shot = webcamRef.current?.getScreenshot();
        if (shot) {
          const base64 = shot.replace(/^data:image\/\w+;base64,/, '');
          onWebcamFrame(base64);
        }
      }, 150);
    }
    return () => {
      if (captureIntervalRef.current) clearInterval(captureIntervalRef.current);
    };
  }, [mode, webcamEnabled, onWebcamFrame]);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file && file.type.startsWith('video/')) onFileSelect(file);
    },
    [onFileSelect]
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => setDragOver(false), []);

  // No content state
  if (!frame && mode === 'upload' && !isStreaming) {
    return (
      <div
        className={`relative flex flex-col items-center justify-center h-full min-h-[400px] card m-2 border-2 border-dashed transition-colors ${
          dragOver ? 'border-safety-orange bg-safety-orange/5' : 'border-slate-600'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <Upload className="w-12 h-12 text-slate-500 mb-3" />
        <p className="text-slate-400 text-sm font-medium">
          Drag & drop a video file here
        </p>
        <p className="text-slate-500 text-xs mt-1">or use the Upload button above</p>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-full m-2">
      {/* Video display */}
      <div className="relative flex-1 card overflow-hidden bg-black flex items-center justify-center">
        {mode === 'webcam' ? (
          <Webcam
            ref={webcamRef}
            audio={false}
            screenshotFormat="image/jpeg"
            videoConstraints={{ facingMode: 'environment', width: 1280, height: 720 }}
            className="w-full h-full object-contain"
          />
        ) : frame ? (
          <img
            src={`data:image/jpeg;base64,${frame}`}
            alt="Video stream"
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="flex flex-col items-center gap-3 text-slate-500">
            {isStreaming ? (
              <>
                <Loader2 className="w-8 h-8 animate-spin text-safety-orange" />
                <span className="text-sm">Connecting to stream...</span>
              </>
            ) : (
              <>
                <Video className="w-10 h-10" />
                <span className="text-sm">Waiting for video feed...</span>
              </>
            )}
          </div>
        )}

        {/* Zone overlay */}
        {(zones?.length > 0 || drawingZone) && (
          <ZoneDrawer
            zones={zones}
            isDrawing={drawingZone}
            onZoneComplete={onZoneComplete}
          />
        )}

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/60 backdrop-blur-sm rounded-full px-2.5 py-1">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs font-medium text-white">LIVE</span>
          </div>
        )}
      </div>

      {/* Stats bar */}
      {(isStreaming || frame) && (
        <div className="flex items-center gap-4 px-3 py-2 bg-slate-800 border-t border-slate-700/50 rounded-b-lg text-xs font-data text-slate-400">
          <span>
            <Camera className="w-3 h-3 inline mr-1" />
            Frames: {stats?.frameCount || 0}
          </span>
          <span>FPS: {stats?.fps || 0}</span>
          {stats?.trackedObjects > 0 && (
            <span>Objects: {stats.trackedObjects}</span>
          )}
          {stats?.riskScore != null && stats.riskScore > 0 && (
            <span className={stats.riskScore > 50 ? 'text-red-400' : 'text-safety-green'}>
              Risk: {Math.round(stats.riskScore)}
            </span>
          )}
          <span className="ml-auto text-slate-500 capitalize">{mode} mode</span>
        </div>
      )}
    </div>
  );
}
