#!/bin/bash

ENVNAME=$(cat ../ENVNAME)

# Check wheather anaconda is installed.
if ! [ -x "$(command -v conda)" ]; then
  echo "Error: anaconda is not installed, quitting..."
  exit 1
fi

echo "Creating conda enviroment $ENVNAME with Python version 3.11"
conda create --name $ENVNAME python=3.11 -y
conda activate $ENVNAME

sleep 2

echo "Installing required Python packages."
cd ../.. && pip install -r ./requirements.txt
