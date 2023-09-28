@echo off
set ENVNAME="hketa-server"

echo Creating conda enviroment %ENVNAME% with Python version 3.11
echo:
call conda create --name %ENVNAME% python=3.11 -y
timeout 2

call conda activate %ENVNAME%

echo Installing required Python packages.
echo:
call pip install -r "%~dp0..\requirements.txt"

pause