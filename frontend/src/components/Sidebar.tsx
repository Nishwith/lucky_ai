import React from "react";
import { useLucky, AGENTS } from "../context/LuckyContext";
import { motion } from "framer-motion";
import { Activity, Zap } from "lucide-react";
import { HudMetrics } from "./HudMetrics";
import "./Sidebar.css";

export const Sidebar = () => {
  const { activeAgent, setActiveAgent, status } = useLucky();

  return (
    <nav className="hud-sidebar">
      <div className="sidebar-label">AGENTS</div>
      {AGENTS.map((agent) => {
        const isActive = activeAgent.id === agent.id;
        return (
          <button
            key={agent.id}
            className={`agent-btn ${isActive ? "active" : ""}`}
            style={
              isActive
                ? ({ "--agent-color": agent.color } as React.CSSProperties)
                : {}
            }
            onClick={() => setActiveAgent(agent)}
          >
            {isActive && (
              <motion.div
                layoutId="agent-indicator"
                className="agent-indicator"
                style={{ background: agent.color }}
                transition={{ type: "spring", stiffness: 400, damping: 35 }}
              />
            )}
            <span
              className="agent-icon"
              style={isActive ? { color: agent.color } : {}}
            >
              {agent.icon}
            </span>
            <span className="agent-label">{agent.id}</span>
            {isActive && (
              <span
                className="agent-active-dot"
                style={{ background: agent.color }}
              />
            )}
          </button>
        );
      })}

      <div className="sidebar-divider" />
      <div className="sidebar-label">SYSTEM</div>
      <div className="sys-stat">
        <Activity size={12} style={{ color: "#00ff88" }} />
        <span>MEM ACTIVE</span>
      </div>
      <div className="sys-stat">
        <Zap size={12} style={{ color: status === "error" ? "#ff6b6b" : "#00d4ff" }} />
        <span>OLLAMA {status === "error" ? "FAIL" : "OK"}</span>
      </div>
      
      {/* Dynamic System Hardware Metrics */}
      <HudMetrics />
    </nav>
  );
};
