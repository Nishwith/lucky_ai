import React from "react";

export interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
  done?: boolean;
}

export interface Agent {
  id: string;
  icon: React.ReactNode;
  color: string;
  key: string;
}

export type SystemState =
  | "DISCONNECTED"
  | "CONNECTING"
  | "READY"
  | "THINKING"
  | "EXECUTING"
  | "SPEAKING"
  | "ERROR";

export interface SystemMetrics {
  cpu: number;
  ram: {
    total: number;
    used: number;
    percent: number;
  };
  disk: {
    total: number;
    used: number;
    percent: number;
  };
  gpu?: {
    gpu_util: number;
    vram_total: number;
    vram_used: number;
  } | null;
}

export interface StartupReport {
  config_ok: boolean;
  sqlite_ok: boolean;
  chroma_ok: boolean;
  ollama_ok: boolean;
  model_ok: boolean;
  degraded_mode: boolean;
  errors: string[];
}

export interface SystemStatus {
  status: "online" | "degraded" | "error" | "thinking";
  system_state: SystemState;
  provider: string;
  model: string;
  startup_report: StartupReport;
}
