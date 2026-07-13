@echo off
cd /d "%~dp0"
echo Memulai Kita Sehat Backend...
python app.py
if %errorlevel% neq 0 (
    echo Gagal menggunakan Python sistem, mencoba menggunakan virtual environment...
    venv\Scripts\python.exe app.py
)
pause
