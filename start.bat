@echo off
title EV-DDSS Server

setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "PYTHON=C:\Users\Vin\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set "OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
set "LOCKFILE=%TEMP%\ev-ddss.lock"
set "APP_PORT=8080"

rem ---- Check lock ----
if exist "%LOCKFILE%" (
    echo.
    echo ERROR: EV-DDSS is already running.
    echo Lock file: %LOCKFILE%
    echo Stop it first or delete the lock file.
    echo.
    pause
    exit /b 1
)

rem ---- Check ports ----
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%APP_PORT% " ^| findstr LISTENING') do (
    echo ERROR: Port %APP_PORT% is already in use by PID %%a
    pause
    exit /b 1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173 " ^| findstr LISTENING') do (
    echo ERROR: Port 5173 is already in use by PID %%a
    pause
    exit /b 1
)

rem ---- Create lock ----
echo %DATE% %TIME% > "%LOCKFILE%"

echo ============================================
echo   EV-DDSS - Starting All Services
echo ============================================
echo.

rem ---- Start Ollama ----
if exist "%OLLAMA%" (
    echo [1/3] Starting Ollama...
    start /B "" "%OLLAMA%" serve >nul 2>&1
    timeout /t 3 /nobreak >nul
) else (
    echo [1/3] Ollama not found - skipping
)

rem ---- Start Backend ----
echo [2/3] Starting Backend on port %APP_PORT%...
pushd "%ROOT%\backend"
set REASONING_TIMEOUT=300
start /B "" "%PYTHON%" -m uvicorn app:create_app --host 0.0.0.0 --port %APP_PORT% --factory --log-level warning >nul 2>&1
popd
timeout /t 8 /nobreak >nul

rem ---- Start Frontend ----
echo [3/3] Starting Frontend on port 5173...
pushd "%ROOT%\frontend"
start /B "" npx.cmd vite --host 0.0.0.0 --port 5173 >nul 2>&1
popd
timeout /t 5 /nobreak >nul

rem ---- Verify ----
echo.
echo ============================================
echo   Service Status
echo ============================================

"%PYTHON%" -c "import urllib.request, json; r=urllib.request.urlopen('http://localhost:'+__import__('os').environ['APP_PORT']+'/health', timeout=8); d=json.loads(r.read()); print('  Backend:  OK' if d.get('status')=='healthy' else '  Backend:  FAIL')" 2>nul
if errorlevel 1 echo   Backend:  FAIL

"%PYTHON%" -c "import urllib.request; r=urllib.request.urlopen('http://localhost:5173', timeout=3); print('  Frontend: OK' if r.status==200 else '  Frontend: FAIL')" 2>nul
if errorlevel 1 echo   Frontend: FAIL

"%PYTHON%" -c "import urllib.request; r=urllib.request.urlopen('http://localhost:11434', timeout=2); print('  Ollama:   OK' if r.status==200 else '  Ollama:   FAIL')" 2>nul
if errorlevel 1 echo   Ollama:   FAIL

echo.
echo ============================================
echo   EV-DDSS is running!
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:%APP_PORT%
echo   API Docs : http://localhost:%APP_PORT%/docs
echo.
echo   To stop, close this window or press Ctrl+C.
echo   Then run:  del "%LOCKFILE%"
echo ============================================
echo.

rem ---- Clean up lock on exit ----
del "%LOCKFILE%" >nul 2>&1
endlocal
