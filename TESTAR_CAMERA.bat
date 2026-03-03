@echo off
title VisionLOL - Teste Rapido
color 0A

echo ========================================
echo   VISIONLOL - TESTE RAPIDO
echo ========================================
echo.
echo Iniciando em 3 segundos...
timeout /t 3 /nobreak >nul

.venv\Scripts\python.exe quick_test.py

pause
