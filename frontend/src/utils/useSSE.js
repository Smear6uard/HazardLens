import { useState, useEffect, useRef, useCallback } from 'react';

export default function useSSE(url) {
  const [frame, setFrame] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({ frameCount: 0, fps: 0, processingTime: 0 });
  const sourceRef = useRef(null);
  const frameCountRef = useRef(0);
  const fpsIntervalRef = useRef(null);

  const connect = useCallback(() => {
    if (!url) return;

    setError(null);
    setIsStreaming(true);
    frameCountRef.current = 0;

    const es = new EventSource(url);
    sourceRef.current = es;

    let framesThisSecond = 0;
    fpsIntervalRef.current = setInterval(() => {
      setStats(prev => ({ ...prev, fps: framesThisSecond }));
      framesThisSecond = 0;
    }, 1000);

    es.addEventListener('frame', (e) => {
      try {
        const data = JSON.parse(e.data);
        setFrame(data.annotated_frame_b64 || data.frame || data.image);
        frameCountRef.current += 1;
        framesThisSecond += 1;
        setStats(prev => ({
          ...prev,
          frameCount: frameCountRef.current,
          riskScore: data.risk_score ?? prev.riskScore,
          complianceRate: data.compliance_rate ?? prev.complianceRate,
          trackedObjects: data.tracked_objects ?? prev.trackedObjects,
        }));
      } catch {
        // raw base64 frame
        setFrame(e.data);
        frameCountRef.current += 1;
        framesThisSecond += 1;
        setStats(prev => ({ ...prev, frameCount: frameCountRef.current }));
      }
    });

    es.addEventListener('alert', (e) => {
      try {
        const alert = JSON.parse(e.data);
        setAlerts(prev => [alert, ...prev].slice(0, 200));
      } catch { /* skip malformed */ }
    });

    es.addEventListener('complete', () => {
      setIsStreaming(false);
      es.close();
    });

    es.onerror = () => {
      setError('Stream connection lost');
      setIsStreaming(false);
      es.close();
    };
  }, [url]);

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    if (fpsIntervalRef.current) {
      clearInterval(fpsIntervalRef.current);
      fpsIntervalRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { frame, alerts, isStreaming, error, stats, disconnect };
}
