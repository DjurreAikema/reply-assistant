@echo off
REM Starts backend and frontend in two windows. Run from the project root.
REM Assumes backend\.venv exists and frontend\node_modules is installed,
REM see README.md for first-time setup.

start "backend" cmd /k "cd backend && .venv\Scripts\activate && python run.py"
start "frontend" cmd /k "cd frontend && npm start"

echo Backend starting on http://localhost:5000
echo Frontend starting on http://localhost:4200
