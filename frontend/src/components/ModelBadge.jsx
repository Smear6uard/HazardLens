import { useState, useEffect } from 'react';
import { Cpu } from 'lucide-react';
import { getHealth } from '../utils/api';

export default function ModelBadge() {
  const [status, setStatus] = useState({ online: false, model: 'YOLO11n' });

  useEffect(() => {
    let mounted = true;

    async function poll() {
      try {
        const data = await getHealth();
        if (mounted) {
          setStatus({
            online: data.model_loaded ?? data.status === 'ok',
            model: data.model_name || 'YOLO11n',
          });
        }
      } catch {
        if (mounted) setStatus(prev => ({ ...prev, online: false }));
      }
    }

    poll();
    const id = setInterval(poll, 10000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  return (
    <div className="flex items-center gap-2 bg-slate-800 border border-slate-700/50 rounded-full px-3 py-1.5">
      <Cpu className="w-3.5 h-3.5 text-slate-400" />
      <span
        className={`w-2 h-2 rounded-full ${
          status.online ? 'bg-safety-green animate-pulse' : 'bg-red-500'
        }`}
      />
      <span className="text-xs font-medium font-data text-slate-300">
        {status.model} {status.online ? 'Ready' : 'Offline'}
      </span>
    </div>
  );
}
