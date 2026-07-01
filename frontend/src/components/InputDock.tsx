import React, { useState, useRef, useCallback } from "react";
import { useLucky, AGENT_COLOR } from "../context/LuckyContext";
import { Send } from "lucide-react";
import "./InputDock.css";

export const InputDock = () => {
  const [input, setInput] = useState("");
  const {
    isLoading,
    setIsLoading,
    activeAgent,
    setMessages,
    sessionId,
    setStatus
  } = useLucky();
  
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return;
    const userText = input.trim();
    setInput("");
    setIsLoading(true);
    setStatus("thinking");

    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: userText }]);

    // Placeholder for assistant message
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", done: false },
    ]);

    try {
      const res = await fetch("http://localhost:8000/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          session_id: sessionId,
          stream: true,
          force_agent: activeAgent.key,
        }),
      });

      if (!res.body) throw new Error("No stream");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let agentDetected = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6);
          if (raw === "[DONE]") {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  done: true,
                  agent: agentDetected,
                };
              }
              return updated;
            });
            break;
          }
          if (raw.startsWith("{")) {
            try {
              const meta = JSON.parse(raw);
              agentDetected = meta.agent || "";
            } catch {}
            continue;
          }
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + raw,
                agent: agentDetected,
              };
            }
            return updated;
          });
        }
      }
    } catch (err) {
      try {
        const res = await fetch("http://localhost:8000/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: userText,
            session_id: sessionId,
            stream: false,
            force_agent: activeAgent.key,
          }),
        });
        const data = await res.json();
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: data.reply,
            agent: data.agent,
            done: true,
          };
          return updated;
        });
      } catch {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content:
              "⚠️ Cannot reach Lucky AI. Is the backend running on port 8000?",
            agent: "system",
            done: true,
          };
          return updated;
        });
        setStatus("error");
      }
    } finally {
      setIsLoading(false);
      setStatus("online");
      inputRef.current?.focus();
    }
  }, [input, isLoading, sessionId, setMessages, setIsLoading, setStatus]);

  const agentColor = AGENT_COLOR[activeAgent.key] || "#00d4ff";

  return (
    <div className="input-dock">
      <div
        className="input-frame"
        style={{ "--agent-color": agentColor } as React.CSSProperties}
      >
        <div className="input-corners">
          <i />
          <i />
          <i />
          <i />
        </div>
        <input
          ref={inputRef}
          className="hud-input"
          placeholder={
            isLoading ? "Processing..." : `Command ${activeAgent.id} ›`
          }
          value={input}
          disabled={isLoading}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          autoFocus
        />
        <button
          className={`send-btn ${isLoading ? "loading" : ""}`}
          onClick={handleSend}
          disabled={isLoading}
          style={{ "--agent-color": agentColor } as React.CSSProperties}
        >
          {isLoading ? (
            <span className="send-spinner" />
          ) : (
            <Send size={16} />
          )}
        </button>
      </div>
      <div className="input-hint">
        ENTER to send · Session{" "}
        <span className="mono">{sessionId.slice(0, 8)}</span>
      </div>
    </div>
  );
};
