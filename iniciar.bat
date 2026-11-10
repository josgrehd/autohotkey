@echo off
title Auto Key Presser
echo ========================================================
echo          Iniciando Auto Key Presser (Python GUI)
echo ========================================================
echo.

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe app.py
) else (
    python app.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Hubo un problema al iniciar la aplicacion.
    pause
)

