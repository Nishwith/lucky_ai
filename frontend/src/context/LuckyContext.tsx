import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Message, Agent, SystemState, SystemMetrics, SystemStatus, PermissionRequest } from "../types";
import { Cpu, Terminal, Sparkles, Briefcase, BookOpen } from "lucide-react";

export const AGENTS: Agent[] = [
  { id: "Main Brain", icon: <Cpu size={16} />, color: "#00d4ff", key: "brain" },
  { id: "Dev Agent", icon: <Terminal size={16} />, color: "#00ff88", key: "coding" },
  { id: "Content Agent", icon: <Sparkles size={16} />, color: "#bf7fff", key: "content" },
  { id: "Business Agent", icon: <Briefcase size={16} />, color: "#ff9900", key: "business" },
  { id: "Study Agent", icon: <BookOpen size={16} />, color: "#ff6b6b", key: "study" },
];

export const AGENT_COLOR: Record<string, string> = {
  brain: "#00d4ff",
  coding: "#00ff88",
  content: "#bf7fff",
  business: "#ff9900",
  study: "#ff6b6b",
  ai_dev: "#00ff88",
  pa: "#00d4ff",
  vision: "#bf7fff",
};

interface LuckyContextType {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  activeAgent: Agent;
  setActiveAgent: (agent: Agent) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  sessionId: string;
  systemState: SystemState;
  setSystemState: (state: SystemState) => void;
  metrics: SystemMetrics | null;
  setMetrics: (metrics: SystemMetrics | null) => void;
  status: "online" | "degraded" | "error" | "thinking";
  setStatus: (status: "online" | "degraded" | "error" | "thinking") => void;
  activeModel: string;
  setActiveModel: (model: string) => void;
  activeProvider: string;
  setActiveProvider: (provider: string) => void;
  refreshSystemStatus: () => Promise<void>;
  pendingPermissions: PermissionRequest[];
  respondToPermission: (requestId: string, approved: boolean, rememberRule?: 'allow' | 'deny' | null) => Promise<void>;
}

const LuckyContext = createContext<LuckyContextType | undefined>(undefined);

export const LuckyProvider = ({ children }: { children: ReactNode }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeAgent, setActiveAgent] = useState<Agent>(AGENTS[0]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  
  const [systemState, setSystemState] = useState<SystemState>("CONNECTING");
  const [status, setStatus] = useState<"online" | "degraded" | "error" | "thinking">("online");
  const [activeModel, setActiveModel] = useState("qwen3:8b");
  const [activeProvider, setActiveProvider] = useState("ollama");
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);

  const refreshSystemStatus = async () => {
    try {
      const r = await fetch("http://localhost:8000/api/system/status");
      const data: SystemStatus = await r.json();
      setActiveModel(data.model);
      setActiveProvider(data.provider);
      setSystemState(data.system_state);
      setStatus(data.status === "degraded" ? "degraded" : "online");
    } catch {
      setSystemState("ERROR");
      setStatus("error");
    }
  };
  const [pendingPermissions, setPendingPermissions] = useState<PermissionRequest[]>([]);

  const pollPermissions = async () => {
    try {
      const r = await fetch("http://localhost:8000/api/permissions/pending");
      if (r.ok) {
        const data = await r.json();
        setPendingPermissions(data.pending || []);
        if (data.system_state) {
          setSystemState(data.system_state);
        }
        if (data.status) {
          setStatus(data.status);
        }
        if (data.model) {
          setActiveModel(data.model);
        }
        if (data.provider) {
          setActiveProvider(data.provider);
        }
      }
    } catch (e) {
      console.error("Error polling permissions:", e);
    }
  };

  const respondToPermission = async (requestId: string, approved: boolean, rememberRule?: 'allow' | 'deny' | null) => {
    try {
      const r = await fetch(`http://localhost:8000/api/permissions/respond/${requestId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          approved,
          remember_rule: rememberRule || null
        })
      });
      if (r.ok) {
        setPendingPermissions(prev => prev.filter(p => p.request_id !== requestId));
      } else {
        console.error("Failed to respond to permission:", await r.text());
      }
    } catch (e) {
      console.error("Error responding to permission:", e);
    }
  };

  useEffect(() => {
    refreshSystemStatus();
    const timer = setInterval(pollPermissions, 800);
    return () => clearInterval(timer);
  }, []);

  return (
    <LuckyContext.Provider
      value={{
        messages,
        setMessages,
        activeAgent,
        setActiveAgent,
        isLoading,
        setIsLoading,
        sessionId,
        systemState,
        setSystemState,
        metrics,
        setMetrics,
        status,
        setStatus,
        activeModel,
        setActiveModel,
        activeProvider,
        setActiveProvider,
        refreshSystemStatus,
        pendingPermissions,
        respondToPermission,
      }}
    >
      {children}
    </LuckyContext.Provider>
  );
};

export const useLucky = () => {
  const context = useContext(LuckyContext);
  if (!context) {
    throw new Error("useLucky must be used within a LuckyProvider");
  }
  return context;
};
