@echo off
set ENVNAME="hketa-server"

echo Starting the ETA server
echo:

call conda activate %ENVNAME% && cd ..\.. && uvicorn app.src.main:app --reload

pause