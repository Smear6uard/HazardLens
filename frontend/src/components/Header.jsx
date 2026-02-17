import { useRef } from 'react';
import { Shield, Upload, Camera, Play, MonitorPlay } from 'lucide-react';
import ModelBadge from './ModelBadge';

export default function Header({ mode, onModeChange, onFileSelect }) {
  const fileRef = useRef(null);

  const modes = [
    { key: 'demo', label: 'Demo', icon: Play },
    { key: 'upload', label: 'Upload', icon: MonitorPlay },
    { key: 'webcam', label: 'Webcam', icon: Camera },
  ];

  function handleFileClick() {
    fileRef.current?.click();
  }

  function handleFile(e) {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
      e.target.value = '';
    }
  }

  return (
    <header className="flex items-center justify-between px-4 py-3 bg-slate-800 border-b border-slate-700/50">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Shield className="w-7 h-7 text-safety-orange" />
          <h1 className="text-lg font-bold tracking-tight">
            <span className="text-safety-orange">Hazard</span>
            <span className="text-white">Lens</span>
          </h1>
        </div>
        <ModelBadge />
      </div>

      <div className="flex items-center gap-2">
        {/* Mode selector */}
        <div className="flex bg-slate-900 rounded-lg p-0.5">
          {modes.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => onModeChange(key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                mode === key
                  ? 'bg-safety-orange text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* Upload button */}
        {mode === 'upload' && (
          <>
            <button onClick={handleFileClick} className="btn-primary flex items-center gap-1.5 text-sm">
              <Upload className="w-3.5 h-3.5" />
              Upload Video
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="video/*"
              onChange={handleFile}
              className="hidden"
            />
          </>
        )}
      </div>
    </header>
  );
}
