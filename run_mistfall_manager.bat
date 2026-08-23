@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    set PY=py
) else (
    set PY=python
)

%PY% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo PySide6 не найден. Устанавливаю...
    %PY% -m pip install -r requirements_mistfall.txt
    if errorlevel 1 (
        echo.
        echo Не удалось установить PySide6.
        pause
        exit /b 1
    )
)

%PY% mistfall_build_manager.py
if errorlevel 1 pause
