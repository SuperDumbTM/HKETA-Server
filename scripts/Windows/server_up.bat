@echo off

set /p ENVNAME=<"%~dp0..\ENVNAME"

echo "Starting the server..."
echo:
call conda activate %ENVNAME% && cd ..\.. && uvicorn app.src.main:app --reload

pause