@echo off
title Sri Modern Rice Mill - Dynamic Billing System
cd /d "%~dp0"
echo ======================================================================
echo   Sri Modern Rice Mill - Dynamic Billing & Accounting System
echo ======================================================================
echo Starting application... Opening in your default browser...
echo.
python -m streamlit run app.py --server.port 8501
pause
