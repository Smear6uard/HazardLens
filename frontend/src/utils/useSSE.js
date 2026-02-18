import { useState, useEffect, useRef } from 'react';

export default function useSSE(url) {
  const [frame, setFrame] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({ frameCount: 0, fps: 0 });
  const frameCountRef = useRef(0);
  const hasReceivedFrameRef = useRef(false);
  const streamStartRef = useRef(0);

  useEffect(() => {
    if (!url) {
      setIsStreaming(false);
      return;
    }

    // Reset state for new connection
    setError(null);
    setFrame(null);
    setAlerts([]);
    setAnalytics(null);
    frameCountRef.current = 0;
    hasReceivedFrameRef.current = false;
    streamStartRef.current = 0;
    setStats({ frameCount: 0, fps: 0 });

    const es = new EventSource(url);
    let alive = true;

    // FPS: compute rolling average from elapsed time
    const fpsInterval = setInterval(() => {
      if (!alive || !streamStartRef.current) return;
      const elapsed = (Date.now() - streamStartRef.current) / 1000;
      const fps = elapsed > 0 ? Math.round(frameCountRef.current / elapsed) : 0;
      setStats(prev => ({ ...prev, fps }));
    }, 500);

    es.addEventListener('frame', (e) => {
      if (!alive) return;
      try {
        const data = JSON.parse(e.data);
        const b64 = data.annotated_frame_b64 || data.frame || data.image;
        if (b64) {
          if (!streamStartRef.current) streamStartRef.current = Date.now();
          setFrame(b64);
          frameCountRef.current += 1;
          hasReceivedFrameRef.current = true;
          setStats(prev => ({
            ...prev,
            frameCount: frameCountRef.current,
            riskScore: data.risk_score ?? prev.riskScore,
            complianceRate: data.compliance_rate ?? prev.complianceRate,
            trackedObjects: data.tracked_objects ?? prev.trackedObjects,
            detections: data.detections ?? prev.detections,
          }));
        }
      } catch {
        setFrame(e.data);
        if (!streamStartRef.current) streamStartRef.current = Date.now();
        frameCountRef.current += 1;
        hasReceivedFrameRef.current = true;
        setStats(prev => ({ ...prev, frameCount: frameCountRef.current }));
      }
    });

    es.addEventListener('alert', (e) => {
      if (!alive) return;
      try {
        const alert = JSON.parse(e.data);
        setAlerts(prev => [alert, ...prev].slice(0, 200));
      } catch { /* skip */ }
    });

    es.addEventListener('analytics', (e) => {
      if (!alive) return;
      try {
        const data = JSON.parse(e.data);
        setAnalytics(data);
      } catch { /* skip */ }
    });

    es.addEventListener('complete', () => {
      setIsStreaming(false);
    });

    es.onopen = () => {
      setIsStreaming(true);
      setError(null);
    };

    es.onerror = () => {
      if (!alive) return;
      if (!hasReceivedFrameRef.current) {
        setError('Stream connection lost — waiting for processing to start...');
      }
    };

    return () => {
      alive = false;
      clearInterval(fpsInterval);
      es.close();
      setIsStreaming(false);
    };
  }, [url]);

  return { frame, alerts, analytics, isStreaming, error, stats };
}
