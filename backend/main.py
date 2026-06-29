"""
Lucky AI — Backend Entry Point
================================
Run this to start Lucky AI's brain.
    uvicorn backend.main:app --reload --port 8000
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.brain.config_loader import CFG, USER_NAME, PROVIDER, MODEL
from backend.memory.sqlite_db    import init_db
from backend.memory.vector_db    import init_vector_db
from backend.api.chat            import router as chat_router
from backend.api.memory          import router as memory_router
from backend.api.system          import router as system_router

from backend.core.logger import setup_logging, logger
from backend.core.startup import run_startup_validation, STARTUP_REPORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured JSON logging
    setup_logging()
    logger.info("Initializing Lucky AI...")
    
    # Run startup validation checks
    report = await run_startup_validation()
    
    from backend.core.state import system_state, SystemState
    if report["degraded_mode"]:
        logger.warning("Lucky AI starting in DEGRADED mode due to validation failures.")
        system_state.transition_to(SystemState.ERROR, "Startup validation failed/degraded")
    else:
        system_state.transition_to(SystemState.READY, "Startup validation passed")
    
    # Run the database initializations
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize SQLite: {e}")
        
    try:
        init_vector_db()
    except Exception as e:
        logger.error(f"Failed to initialize Vector DB: {e}")
        
    logger.info("Lucky AI initialization complete.")
    yield
    logger.info("Shutting down Lucky AI...")


app = FastAPI(
    title       = "Lucky AI",
    description = f"Personal AI OS for {USER_NAME} — powered by {MODEL} via {PROVIDER}",
    version     = "1.0.0",
    docs_url    = "/docs",
    lifespan    = lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",   # Tauri dev server
        "http://localhost:3000",   # React fallback
        "http://127.0.0.1:1420",
        "http://127.0.0.1:3000",
        "tauri://localhost",       # Tauri production build
    ],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(chat_router,   prefix="/api", tags=["Chat"])
app.include_router(memory_router, prefix="/api", tags=["Memory"])
app.include_router(system_router, prefix="/api", tags=["System"])


@app.get("/")
async def root():
    return JSONResponse({
        "message": f"🍀 Lucky AI is running. Hello, {USER_NAME}!",
        "docs":    "http://localhost:8000/docs",
        "chat":    "POST http://localhost:8000/api/chat",
        "status":  "GET http://localhost:8000/api/system/status"
    })
