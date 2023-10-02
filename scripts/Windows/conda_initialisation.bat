@echo off
set /p ENVNAME=<"%~dp0..\ENVNAME"

REM Check wheather anaconda is installed.
WHERE /q conda
IF ERRORLEVEL 1 (
    echo "Error: anaconda is not installed, quitting..."
    exit 1
)

echo "Creating conda enviroment %ENVNAME% with Python version 3.11"
echo:
call conda create --name %ENVNAME% python=3.11 -y
timeout 2

call conda activate %ENVNAME%

echo "Installing required Python packages."
echo:
call pip install -r "%~dp0..\..\requirements.txt"

pause