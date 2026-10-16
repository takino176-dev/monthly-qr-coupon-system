@echo off
title QR Coupon System Launcher
echo Starting QR Coupon System...
cd /d C:\Monthly_QR_Coupon_System
call .venv\Scripts\activate.bat
start http://127.0.0.1:5000
python app.py
pause