import { useLucky } from "../context/LuckyContext";
import { useSystemMetrics } from "../hooks/useSystemMetrics";
import "./HudMetrics.css";

export const HudMetrics = () => {
  // Initialize polling hook
  useSystemMetrics();
  
  const { metrics } = useLucky();

  if (!metrics) {
    return (
      <div className="hud-metrics-container loading-telemetry">
        <div className="sidebar-label">TELEMETRY</div>
        <span className="loading-text">LOADING SENSORS...</span>
      </div>
    );
  }

  const formatBytes = (bytes: number) => {
    const gb = bytes / (1024 * 1024 * 1024);
    return `${gb.toFixed(1)} GB`;
  };

  return (
    <div className="hud-metrics-container">
      <div className="sidebar-label">TELEMETRY</div>
      
      <div className="metric-row">
        <span className="metric-label">CPU</span>
        <div className="metric-bar-container">
          <div 
            className="metric-bar" 
            style={{ width: `${metrics.cpu}%`, backgroundColor: "var(--hud-cyan)" }} 
          />
        </div>
        <span className="metric-val">{metrics.cpu.toFixed(0)}%</span>
      </div>

      <div className="metric-row">
        <span className="metric-label">RAM</span>
        <div className="metric-bar-container">
          <div 
            className="metric-bar" 
            style={{ width: `${metrics.ram.percent}%`, backgroundColor: "var(--hud-green)" }} 
          />
        </div>
        <span className="metric-val">{metrics.ram.percent.toFixed(0)}%</span>
      </div>

      <div className="metric-row">
        <span className="metric-label">DISK</span>
        <div className="metric-bar-container">
          <div 
            className="metric-bar" 
            style={{ width: `${metrics.disk.percent}%`, backgroundColor: "var(--hud-purple)" }} 
          />
        </div>
        <span className="metric-val">{metrics.disk.percent.toFixed(0)}%</span>
      </div>

      {metrics.gpu && (
        <>
          <div className="metric-row">
            <span className="metric-label">GPU</span>
            <div className="metric-bar-container">
              <div 
                className="metric-bar" 
                style={{ width: `${metrics.gpu.gpu_util}%`, backgroundColor: "var(--hud-orange)" }} 
              />
            </div>
            <span className="metric-val">{metrics.gpu.gpu_util.toFixed(0)}%</span>
          </div>

          <div className="metric-row">
            <span className="metric-label">VRAM</span>
            <div className="metric-bar-container">
              <div 
                className="metric-bar" 
                style={{ 
                  width: `${(metrics.gpu.vram_used / metrics.gpu.vram_total) * 100}%`, 
                  backgroundColor: "var(--hud-orange)" 
                }} 
              />
            </div>
            <span className="metric-val">
              {formatBytes(metrics.gpu.vram_used)}
            </span>
          </div>
        </>
      )}
    </div>
  );
};
