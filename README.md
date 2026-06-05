# 🍀 Lucky AI — Personal AI Operating System

> Your personal AI that remembers you, speaks your language, and executes real work.
> 100% offline. Zero subscription. Completely yours.

---

## ⚡ Quick Start (Day 1)

### 1. Install Ollama
Download from [ollama.com](https://ollama.com) and install on Windows.

### 2. Pull Qwen3 (one time, ~5GB)
```bash
ollama pull qwen3:8b
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure your name
Edit `config.json`:
```json
{
  "lucky": {
    "user_name": "YourName"
  }
}
```

### 5. Start Lucky AI
```bash
# Option A: Double-click
start_lucky.bat

# Option B: Terminal
python -m uvicorn backend.main:app --reload --port 8000
```

### 6. Test it works
```bash
python test_lucky.py
```

### 7. Open API docs
Visit: http://localhost:8000/docs

---

## 💬 Chat with Lucky

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hey Lucky, what can you do?", "stream": false}'
```

---

## 🔌 Switch AI Provider (one line change)

Edit `config.json` — nothing else changes:

```json
// Local (default, free, private)
{ "provider": "ollama", "model": "qwen3:8b", "api_key": "" }

// Groq (free tier, fastest)
{ "provider": "groq", "model": "llama-3.3-70b-versatile", "api_key": "gsk_..." }

// OpenAI
{ "provider": "openai", "model": "gpt-4o-mini", "api_key": "sk-..." }

// Anthropic
{ "provider": "anthropic", "model": "claude-haiku-4-5-20251001", "api_key": "sk-ant-..." }
```

---

## 📁 Project Structure

```
lucky-ai/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── brain/
│   │   ├── universal_brain.py   # LiteLLM wrapper — works with any AI
│   │   ├── model_router.py      # Auto-routes to best model per task
│   │   ├── prompt_builder.py    # Builds personalised system prompts
│   │   └── config_loader.py     # Reads config.json
│   ├── memory/
│   │   ├── sqlite_db.py     # Projects, tasks, personal info
│   │   └── vector_db.py     # ChromaDB semantic memory
│   └── api/
│       ├── chat.py          # /chat endpoint (stream + regular)
│       └── memory.py        # /memory endpoints
├── config.json              # Your settings — change provider here
├── requirements.txt
├── start_lucky.bat          # One-click Windows start
└── test_lucky.py            # Verify everything works
```

---

## 🚀 What's Next (Days 2–30)

- [ ] Day 2–7: Tauri React frontend
- [ ] Day 8: Dev Agent (code generation + file creation)
- [ ] Day 9: Content Agent (scripts, SEO, YouTube)
- [ ] Day 10: PA Agent (projects, briefings, deadlines)
- [ ] Day 13: Voice (Whisper + Piper TTS)
- [ ] Day 19: Parallel task queue
- [ ] Day 20: smolagents integration
- [ ] Day 25: FLUX image generation
- [ ] Day 30: Lucky AI v1.0 complete

---

## 🌐 Open Source

Lucky AI is being built to open source. Architecture is provider-agnostic from Day 1.
Anyone can use it with Ollama (local, free) or any cloud AI API.

License: MIT (when published)

---

*Built by one person. For everyone.*
