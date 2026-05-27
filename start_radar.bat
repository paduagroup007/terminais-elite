@echo off
title TITAN GLOBAL WHALE RADAR - Launcher
echo [SISTEMA] Iniciando Hub de Monitoramento de Baleias Internacionais...
cd /d "C:\Users\padua\.gemini\antigravity\scratch\titan_global_whale_radar"
python -m streamlit run app.py --browser.gatherUsageStats false
pause
