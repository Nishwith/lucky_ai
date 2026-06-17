import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Terminal,
  Cpu,
  Sparkles,
  Send,
  Bot,
  User,
  Briefcase,
  BookOpen,
  Loader2,
} from "lucide-react";
import "./App.css";

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
}

function App() {
  const [input, setInput] = useState("");
  const [activeAgent, setActiveAgent] = useState("Main Brain");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Generates a session ID once per load to track conversation history
  const [sessionId] = useState(() => crypto.randomUUID());

  const bottomRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Bulletproof Auto-scroll (only scrolls the container, never the page)
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isLoading]);

  // Track mouse for the glowing quantum grid background
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      document.documentElement.style.setProperty("--mouse-x", `${e.clientX}px`);
      document.documentElement.style.setProperty("--mouse-y", `${e.clientY}px`);
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  const agents = [
    { id: "Main Brain", icon: <Cpu size={18} /> },
    { id: "Dev Agent", icon: <Terminal size={18} /> },
    { id: "Content Agent", icon: <Sparkles size={18} /> },
    { id: "Business Agent", icon: <Briefcase size={18} /> },
    { id: "Study Agent", icon: <BookOpen size={18} /> },
  ];

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userText = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          session_id: sessionId,
          stream: false,
        }),
      });

      if (!response.ok) throw new Error(`Backend error: ${response.status}`);

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply, agent: data.agent },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "⚠️ Could not reach Lucky AI backend. Is it running on port 8000?",
          agent: "system",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* ── Backgrounds & Overlays ── */}
      <div className="tech-bg" />
      <div className="scanner" />

      {/* ── Top HUD ── */}
      <header className="top-hud">
        <div className="hud-brand">
          <span className="brand-text">LUCKY</span>
          <span className="hud-status online">● ONLINE</span>
        </div>
        <div className="hud-metrics">
          <div className="metric">
            <span>CPU</span> 45%
          </div>
          <div className="metric">
            <span>RAM</span> 8.2 GB
          </div>
          <div className="metric">
            <span>GPU</span> 65%
          </div>
          <div className="metric">
            <span>MODEL</span> Qwen3
          </div>
        </div>
      </header>

      {/* ── Main Layout ── */}
      <div className="os-layout">
        {/* 1. Left Panel (Agents & History) */}
        <nav className="sidebar">
          <div className="panel-section">
            <h3 className="section-title">ACTIVE AGENTS</h3>
            <div className="agent-list">
              {agents.map((agent) => {
                const isActive = activeAgent === agent.id;
                return (
                  <button
                    key={agent.id}
                    className={`agent-item ${isActive ? "active" : ""}`}
                    onClick={() => setActiveAgent(agent.id)}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="active-indicator"
                        className="active-indicator"
                        transition={{
                          type: "spring",
                          stiffness: 300,
                          damping: 30,
                        }}
                      />
                    )}
                    {agent.icon}
                    {agent.id}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="panel-section" style={{ marginTop: "auto" }}>
            <h3 className="section-title">SESSION HISTORY</h3>
            <div className="history-item">Current Session</div>
            <div className="history-item dim">Yesterday's Build</div>
            <div className="history-item dim">API Debugging</div>
          </div>
        </nav>

        {/* 2. Center Canvas (Chat area) */}
        <main className="chat-canvas">
          <div className="messages-container" ref={messagesContainerRef}>
            {messages.length === 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="message-row ai"
              >
                <div className="avatar ai">
                  <Bot size={20} />
                </div>
                <div className="message-content">
                  System initialized. Memory loaded.
                  <br />
                  <br />
                  Routed to <strong>{activeAgent}</strong>. How can I help you
                  today?
                </div>
              </motion.div>
            )}

            <AnimatePresence>
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`message-row ${msg.role === "user" ? "user" : "ai"}`}
                >
                  <div
                    className={`avatar ${msg.role === "assistant" ? "ai" : ""}`}
                  >
                    {msg.role === "assistant" ? (
                      <Bot size={20} />
                    ) : (
                      <User size={20} />
                    )}
                  </div>
                  <div className="message-content">
                    {msg.role === "assistant" &&
                      msg.agent &&
                      msg.agent !== "system" && (
                        <div className="agent-tag">{msg.agent} agent</div>
                      )}
                    {msg.content.split("\n").map((line, j) => (
                      <span key={j}>
                        {line}
                        {j < msg.content.split("\n").length - 1 && <br />}
                      </span>
                    ))}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="message-row ai"
              >
                <div className="avatar ai">
                  <Bot size={20} />
                </div>
                <div
                  className="message-content"
                  style={{ display: "flex", gap: "8px", alignItems: "center" }}
                >
                  <Loader2
                    size={16}
                    className="spin"
                    style={{ color: "var(--cyan)" }}
                  />
                  <span style={{ color: "var(--cyan)", opacity: 0.8 }}>
                    Lucky is thinking...
                  </span>
                </div>
              </motion.div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="input-dock">
            <div className="input-wrapper">
              <input
                type="text"
                className="tech-input"
                placeholder={
                  isLoading ? "Processing..." : `Message ${activeAgent}...`
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                disabled={isLoading}
              />
              <button
                className="send-action"
                onClick={handleSend}
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 size={20} className="spin" color="#000" />
                ) : (
                  <Send size={20} color="#000" />
                )}
              </button>
            </div>
          </div>
        </main>

        {/* 3. Right Panel (Performance & Memory) */}
        <aside className="sidebar right-panel">
          <div className="panel-section">
            <h3 className="section-title">SYSTEM TASKS</h3>
            <div className="task-item">
              <div
                style={{ color: "#fff", marginBottom: "4px", fontSize: "13px" }}
              >
                Idle
              </div>
              <div style={{ color: "#9fb6d3", fontSize: "11px" }}>
                Awaiting Input
              </div>
            </div>
          </div>

          <div className="panel-section">
            <h3 className="section-title">CONTEXT MEMORY</h3>
            <div className="memory-card">
              No specific context loaded for this session yet.
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}

export default App;
