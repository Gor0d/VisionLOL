@echo off
title VisionLOL - Diagnostico de Camera
color 0E

echo ======================================
echo   DIAGNOSTICO DE CAMERA
echo ======================================
echo.
echo Este script ira:
echo  1. Verificar programas usando camera
echo  2. Testar todos os indices de camera
echo  3. Fazer teste detalhado
echo.
echo Pressione qualquer tecla para continuar...
pause >nul

.venv\Scripts\python.exe diagnose_camera.py

echo.
echo ======================================
pause
