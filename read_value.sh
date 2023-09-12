#!/bin/bash



# Check if a key is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <key>"
    exit 1
fi

KEY=$1

# Assuming your virtual environment is in a folder called 'venv' next to your script.
DIR="/Users/danthompson/Code/Tools/CLI/toggl_textbar/"
FILE_PATH="$DIR/print_utility_value.py"
ACTIVATE_PATH="$DIR/.venv/bin/activate"

# Activate the virtual environment
source $ACTIVATE_PATH

# Run the Python script
python $FILE_PATH "$KEY"

# Deactivate the virtual environment
deactivate
