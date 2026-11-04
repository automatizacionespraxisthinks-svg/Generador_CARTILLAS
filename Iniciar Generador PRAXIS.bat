@echo off
title Generador de cartillas PRAXIS - THINKS
cd /d "%~dp0"
echo Abriendo el Generador de cartillas en el navegador...
echo No cierres esta ventana mientras uses el sistema.
".venv\Scripts\python.exe" iniciar.py
pause
