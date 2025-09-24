@echo off
echo Setting up DocuShield Backend...

cd backend

echo Installing minimal dependencies first...
pip install -r requirements-minimal.txt

if %errorlevel% equ 0 (
    echo ✅ Minimal setup complete!
    echo.
    echo To install optional dependencies later:
    echo   pip install -r requirements-optional.txt
    echo.
    echo To run the backend:
    echo   python main.py
) else (
    echo ❌ Installation failed. Try installing dependencies individually:
    echo   pip install fastapi uvicorn pydantic sqlalchemy pymysql
)

pause
