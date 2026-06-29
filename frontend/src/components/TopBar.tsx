import { useState, useEffect } from "react";
import { useLucky } from "../context/LuckyContext";
import { Wifi, Zap, Clock } from "lucide-react";
import "./TopBar.css";

function LiveClock() {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return <span className="hud-clock">{time.toTimeString().slice(0, 8)}</span>;
}

export const TopBar = () => {
  const { status, systemState, activeModel, activeProvider } = useLucky();

  return (
    <header className="hud-topbar">
      <div className="hud-logo">
        <span className="logo-mark">⬡</span>
        <span className="logo-text">
          LUCKY<span className="logo-ai"> AI</span>
        </span>
      </div>

      <div className="hud-status-row">
        <div className={`status-pill ${status}`}>
          <span className="status-dot" />
          <span>
            {systemState === "THINKING" ? "PROCESSING" : systemState}
          </span>
        </div>
        <div className="hud-meta">
          <Wifi size={12} /> LOCAL
        </div>
        <div className="hud-meta">
          <Zap size={12} /> {activeModel} ({activeProvider})
        </div>
        <div className="hud-meta">
          <Clock size={12} /> <LiveClock />
        </div>
      </div>
    </header>
  );
};
