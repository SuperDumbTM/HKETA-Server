@echo off

for /d /r "%~dp0..\..\app" %%i in (__pycache__) do (
    echo Deleting "%%i"...
    rd /s /q "%%i"
)

pause