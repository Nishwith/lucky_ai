import { useState } from "react";
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
} from "lucide-react";
import "./App.css";

function App() {
  const [input, setInput] = useState("");
  const [activeAgent, setActiveAgent] = useState("Main Brain");

  const agents = [
    { id: "Main Brain", icon: <Cpu size={18} /> },
    { id: "Dev Agent", icon: <Terminal size={18} /> },
    { id: "Content Agent", icon: <Sparkles size={18} /> },
    { id: "Business Agent", icon: <Briefcase size={18} /> },
    { id: "Study Agent", icon: <BookOpen size={18} /> },
  ];

const handleSend = async () => {
  if (!input.trim()) return;

  const payload = {
    prompt: input,
    model: activeAgent === "Dev Agent" ? "qwen2.5-coder:7b" : "qwen3:8b"
  };

  try {
    const response = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    
    const data = await response.json();
    console.log("Lucky AI Response:", data.response);
    
    // In the next step, we'll map this 'data.response' to your chat history UI!
  } catch (err) {
    console.error("Connection error:", err);
  }
  
  setInput("");
};

  return (
    <>
      <div className="tech-bg" />
      <div className="scanner" />

      <div className="os-layout">
        {/* Borderless Sidebar */}
        <nav className="sidebar">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="brand-header"
          >
            <div className="brand-text">LUCKY AI</div>
          </motion.div>

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
        </nav>

        {/* Chat Canvas */}
        <main className="chat-canvas">
          <div className="messages-container">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="message-row ai"
            >
              <div className="avatar ai">
                <Bot size={20} />
              </div>
              <div className="message-content">
                System initialized. Memory loaded.
                <br />
                <br />
                Currently routed to <strong>{activeAgent}</strong>. How can I
                help you today?
              </div>
            </motion.div>
          </div>

          {/* Input Dock */}
          <div className="input-dock">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="input-wrapper"
            >
              <div className="input-glow" />
              <input
                type="text"
                className="tech-input"
                placeholder={`Send a command to ${activeAgent}...`}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
              />
              <button className="send-action" onClick={handleSend}>
                <Send size={20} />
              </button>
            </motion.div>
          </div>
        </main>
      </div>
    </>
  );
}

export default App;
