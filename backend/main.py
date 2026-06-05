"""
Lucky AI — Backend Entry Point
================================
Run this to start Lucky AI's brain.
    uvicorn backend.main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Make sure imports work from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.brain.config_loader import CFG, USER_NAME, PROVIDER, MODEL
from backend.memory.sqlite_db    import init_db
from backend.memory.vector_db    import init_vector_db
from backend.api.chat            import router as chat_router
from backend.api.memory          import router as memory_router

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Lucky AI",
    description = f"Personal AI OS for {USER_NAME} — powered by {MODEL} via {PROVIDER}",
    version     = "1.0.0",
    docs_url    = "/docs",
)

# Allow Tauri frontend + any local requests
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat_router,   prefix="/api", tags=["Chat"])
app.include_router(memory_router, prefix="/api", tags=["Memory"])


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    print("\n" + "="*50)
    print("  🍀 Lucky AI — Personal AI Operating System")
    print("="*50)
    print(f"  User:     {USER_NAME}")
    print(f"  Provider: {PROVIDER}")
    print(f"  Model:    {MODEL}")
    print(f"  Docs:     http://localhost:8000/docs")
    print("="*50 + "\n")

    # Init databases
    init_db()
    init_vector_db()
    print("[Lucky AI] All systems ready. Let's go! 🚀\n")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status":   "online",
        "name":     "Lucky AI",
        "user":     USER_NAME,
        "provider": PROVIDER,
        "model":    MODEL,
    }


@app.get("/")
async def root():
    return JSONResponse({
        "message": f"🍀 Lucky AI is running. Hello, {USER_NAME}!",
        "docs":    "http://localhost:8000/docs",
        "chat":    "POST http://localhost:8000/api/chat",
    })
