
@echo off
echo ===============================================
echo   CREARE EXECUTABIL MONITOR PULS + RESPIRATIE (V10)
echo ===============================================
echo.
echo Stergere build-uri vechi...
rmdir /s /q build
rmdir /s /q dist
del /f /q pulse_breath_monitor_v10.spec

echo Construire executabil...
pyinstaller --onefile --noconsole ^
--hidden-import openpyxl ^
--hidden-import openpyxl.workbook ^
--hidden-import openpyxl.worksheet ^
pulse_breath_monitor_v10.py

if %ERRORLEVEL% NEQ 0 (
    echo Eroare la generarea executabilului!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Executabilul a fost generat cu succes in folderul DIST!
pause
