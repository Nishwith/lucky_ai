@echo off
title Lucky AI — Starting...
color 0A

echo.
echo  ==========================================
echo   Lucky AI — Personal AI Operating System
echo  ==========================================
echo.

:: Check Ollama is running
echo [1/3] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Ollama not running. Starting Ollama...
    start /B ollama serve
    timeout /t 3 /nobreak >nul
) else (
    echo [OK] Ollama is running
)

:: Check if model is available
echo [2/3] Checking Qwen3 model...
ollama list | findstr "qwen3" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Qwen3 not found. Pulling now ^(~5GB^)...
    echo     This is a one-time download. Please wait...
    ollama pull qwen3:8b
)
echo [OK] Model ready

:: Start Lucky AI backend
echo [3/3] Starting Lucky AI backend...
echo.
echo  Lucky AI is running at:
echo   Brain:  http://localhost:8000
echo   Docs:   http://localhost:8000/docs
echo   Chat:   POST http://localhost:8000/api/chat
echo.
echo  Press Ctrl+C to stop
echo.

cd /d "%~dp0"
call venv\Scripts\activate
set CHROMA_TELEMETRY=false
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause