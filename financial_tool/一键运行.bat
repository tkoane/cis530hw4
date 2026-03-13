@echo off
chcp 65001 >nul
echo ================================================
echo   金融高频数据自动化整理工具
echo ================================================
echo.
cd /d "%~dp0"
python process_data.py
echo.
pause
