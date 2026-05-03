@echo off
echo ======================================================================
echo   HydroQuote AI - Demo Launcher
echo ======================================================================
echo.
echo This will start both the backend and frontend servers.
echo.
echo Press Ctrl+C in each window to stop the servers.
echo.
pause

echo.
echo Starting Backend Server...
start "HydroQuote AI - Backend" cmd /k "python start_backend.py"

timeout /t 3 /nobreak >nul

echo Starting Frontend Server...
start "HydroQuote AI - Frontend" cmd /k "python serve_frontend.py"

echo.
echo ======================================================================
echo   Both servers are starting!
echo ======================================================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo The frontend will open in your browser automatically.
echo.
pause

@REM Made with Bob
