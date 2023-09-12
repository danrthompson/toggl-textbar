#!/bin/bash

# Assuming your virtual environment is in a folder called 'venv' next to your script.
DIR="/Users/danthompson/Code/Tools/CLI/toggl_textbar/"
FILE_PATH="$DIR/update_all_datasources.py"
ACTIVATE_PATH="$DIR/.venv/bin/activate"

# Activate the virtual environment
source $ACTIVATE_PATH

# Run the Python script
python $FILE_PATH

# Deactivate the virtual environment
deactivate
