@echo off
chcp 65001 > nul
set PYTHONUTF8=1
title The Witcher 3 - Vietnamese Voiceover Companion

:menu
cls
echo =================================================================
echo        THE WITCHER 3 - VIETNAMESE VOICEOVER COMPANION
echo =================================================================
echo.
echo  PHIM NONG TRONG GAME: Nhan [F10] hoac [F8] bat ky luc nao khi choi
echo  de chuyen doi qua lai giua cac che do ma khong can thoat game!
echo.
echo -----------------------------------------------------------------
echo  [1] Chay Thuyet minh OFFLINE VITS (Piper ONNX - Sieu toc ~0.4s)
echo      - 100%% tren may, khong can mang, phan xa cuc nhanh khi doi thoai
echo.
echo  [2] Chay Thuyet minh OFFLINE KOKORO (Kokoro ONNX - Diem Trinh)
echo      - 100%% tren may, giong nu rat tu nhien va truyen cam
echo.
echo  [3] Chay Thuyet minh ONLINE (Edge-TTS Cloud - Hoai My)
echo      - Giong doc dien anh, tu dong cuu nguy sang Offline neu dut mang
echo.
echo  [4] Thu nghiem thoai mau OFFLINE VITS (Test Mode)
echo  [5] Thu nghiem thoai mau OFFLINE KOKORO (Test Mode)
echo  [6] Thu nghiem thoai mau ONLINE Edge-TTS (Test Mode)
echo.
echo  [7] Cai dat / Cap nhat toan bo thu vien
echo  [8] Thoat
echo =================================================================
set /p choice="Nhap lua chon cua ban (1/2/3/4/5/6/7/8): "

if "%choice%"=="1" (
    cls
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*voiceover_reader.py*' } | Stop-Process -Force" > nul 2>&1
    python "%~dp0voiceover_reader.py" --engine=vits
    pause
    goto menu
) else if "%choice%"=="2" (
    cls
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*voiceover_reader.py*' } | Stop-Process -Force" > nul 2>&1
    python "%~dp0voiceover_reader.py" --engine=kokoro
    pause
    goto menu
) else if "%choice%"=="3" (
    cls
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*voiceover_reader.py*' } | Stop-Process -Force" > nul 2>&1
    python "%~dp0voiceover_reader.py" --engine=online
    pause
    goto menu
) else if "%choice%"=="4" (
    cls
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*voiceover_reader.py*' } | Stop-Process -Force" > nul 2>&1
    python "%~dp0voiceover_reader.py" --engine=vits --test
    pause
    goto menu
) else if "%choice%"=="5" (
    cls
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*voiceover_reader.py*' } | Stop-Process -Force" > nul 2>&1
    python "%~dp0voiceover_reader.py" --engine=kokoro --test
    pause
    goto menu
) else if "%choice%"=="6" (
    cls
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*voiceover_reader.py*' } | Stop-Process -Force" > nul 2>&1
    python "%~dp0voiceover_reader.py" --engine=online --test
    pause
    goto menu
) else if "%choice%"=="7" (
    cls
    echo Dang cai dat / cap nhat toan bo thu vien can thiet...
    pip install edge-tts sounddevice soundfile numpy onnxruntime vig2p
    echo Hoan tat!
    pause
    goto menu
) else (
    exit
)
