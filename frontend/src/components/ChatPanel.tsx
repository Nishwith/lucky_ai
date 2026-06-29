import { useRef, useEffect } from "react";
import { useLucky, AGENT_COLOR } from "../context/LuckyContext";
import { motion, AnimatePresence } from "framer-motion";
import { Cpu } from "lucide-react";
import "./ChatPanel.css";

function renderContent(text: string) {
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      const lines = part.slice(3, -3).split("\n");
      const lang = lines[0].trim() || "code";
      const code = lines.slice(1).join("\n").trim();
      return (
        <div key={i} className="code-block">
          <div className="code-lang">{lang}</div>
          <pre className="code-content">
            <code>{code}</code>
          </pre>
        </div>
      );
    }
    return (
      <span key={i}>
        {part.split("\n").map((line, j, arr) => (
          <span key={j}>
            {line}
            {j < arr.length - 1 && <br />}
          </span>
        ))}
      </span>
    );
  });
}

export const ChatPanel = () => {
  const { messages, activeAgent, activeModel } = useLucky();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const agentColor = AGENT_COLOR[activeAgent.key] || "#00d4ff";

  return (
    <div className="chat-area">
      {/* Welcome panel */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="msg-panel assistant"
      >
        <div
          className="msg-agent-badge"
          style={{ color: agentColor, borderColor: `${agentColor}40` }}
        >
          {activeAgent.icon} {activeAgent.id}
        </div>
        <div className="msg-body">
          System initialised. Memory loaded. Running on{" "}
          <strong>{activeModel}</strong>.
          <br />
          Route active:{" "}
          <strong style={{ color: agentColor }}>{activeAgent.id}</strong>.
          What do you need?
        </div>
        <div className="msg-corners">
          <i />
          <i />
          <i />
          <i />
        </div>
      </motion.div>

      {/* Messages */}
      <AnimatePresence>
        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className={`msg-panel ${msg.role}`}
          >
            {msg.role === "assistant" && msg.agent && (
              <div
                className="msg-agent-badge"
                style={{
                  color: AGENT_COLOR[msg.agent] || agentColor,
                  borderColor: `${AGENT_COLOR[msg.agent] || agentColor}40`,
                }}
              >
                <Cpu size={11} />
                {msg.agent.toUpperCase()} AGENT
              </div>
            )}
            {msg.role === "user" && (
              <div className="msg-user-badge">YOU</div>
            )}
            <div className="msg-body">
              {msg.role === "assistant" &&
              !msg.done &&
              msg.content === "" ? (
                <div className="thinking-dots">
                  <span />
                  <span />
                  <span />
                </div>
              ) : (
                renderContent(msg.content)
              )}
              {msg.role === "assistant" &&
                !msg.done &&
                msg.content !== "" && (
                  <span className="cursor-blink">▋</span>
                )}
            </div>
            <div className="msg-corners">
              <i />
              <i />
              <i />
              <i />
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      <div ref={bottomRef} />
    </div>
  );
};
