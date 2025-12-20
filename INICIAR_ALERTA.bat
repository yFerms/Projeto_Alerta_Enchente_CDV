@echo off
echo --- INICIANDO SISTEMA DE ALERTA RIO PIRACICABA ---
cd /d "%~dp0"
python monitor_definitivo.py
pause