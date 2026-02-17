import { useState, useEffect, useRef } from 'react';

export default function useSSE(url) {
  const [frame, setFrame] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({ frameCount: 0, fps: 0 });
  const fpsCounterRef = useRef(0);
  const frameCountRef = useRef(0);

  useEffect(() => {
    if (!url) {
      setIsStreaming(false);
      return;
    }

    // Reset state for new connection
    setError(null);
    setFrame(null);
    setAlerts([]);
    frameCountRef.current = 0;
    fpsCounterRef.current = 0;
    setStats({ frameCount: 0, fps: 0 });

    const es = new EventSource(url);
    let alive = true;

    // FPS counter
    const fpsInterval = setInterval(() => {
      if (!alive) return;
      setStats(prev => ({
        ...prev,
        fps: fpsCounterRef.current,
      }));
      fpsCounterRef.current = 0;
    }, 1000);

    es.addEventListener('frame', (e) => {
      if (!alive) return;
      try {
        const data = JSON.parse(e.data);
        const b64 = data.annotated_frame_b64 || data.frame || data.image;
        if (b64) {
          setFrame(b64);
          frameCountRef.current += 1;
          fpsCounterRef.current += 1;
          setStats(prev => ({
            ...prev,
            frameCount: frameCountRef.current,
            riskScore: data.risk_score ?? prev.riskScore,
            complianceRate: data.compliance_rate ?? prev.complianceRate,
            trackedObjects: data.tracked_objects ?? prev.trackedObjects,
          }));
        }
      } catch {
        // raw base64 string
        setFrame(e.data);
        frameCountRef.current += 1;
        fpsCounterRef.current += 1;
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

    es.addEventListener('complete', () => {
      setIsStreaming(false);
    });

    es.onopen = () => {
      setIsStreaming(true);
    };

    es.onerror = () => {
      if (!alive) return;
      setError('Stream connection lost');
      setIsStreaming(false);
    };

    return () => {
      alive = false;
      clearInterval(fpsInterval);
      es.close();
      setIsStreaming(false);
    };
  }, [url]);

  return { frame, alerts, isStreaming, error, stats };
}
