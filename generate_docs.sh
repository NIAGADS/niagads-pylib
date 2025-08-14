#!/bin/bash

# Define the source directories and the output directory
SOURCE_DIRS=("bases/niagads" "components/niagads")
OUTPUT_DIR="docs"

# Ensure lazydocs is installed
if ! command -v lazydocs &> /dev/null
then
    echo "lazydocs could not be found. Please install it using 'pipx install lazydocs'."
    exit 1
fi

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Set PYTHONPATH to the project root directory
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Check for the existence of the poetry.lock file
if [ ! -f "poetry.lock" ]; then
    echo "Error: poetry.lock file not found. Please ensure you are in the correct project directory."
    exit 1
fi

# Get the Python executable path directly from Poetry
POETRY_PYTHON_EXEC=$(poetry env info -p)/bin/python
POETRY_PYTHON_VERSION=$($POETRY_PYTHON_EXEC -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
POETRY_MAJOR_VERSION=$(echo "$POETRY_PYTHON_VERSION" | cut -d. -f1)
POETRY_MINOR_VERSION=$(echo "$POETRY_PYTHON_VERSION" | cut -d. -f2)

# Check if the Poetry environment Python version is > 3.12
if [ "$POETRY_MAJOR_VERSION" -gt 3 ] || { [ "$POETRY_MAJOR_VERSION" -eq 3 ] && [ "$POETRY_MINOR_VERSION" -ge 12 ]; }; then
    echo "Poetry environment Python version is > 3.12. Using pyenv to run Python 3.10.4."
    PYENV_PYTHON_EXEC=$(pyenv which python3.10)
    for SRC_DIR in "${SOURCE_DIRS[@]}"
    do
        echo "Generating documentation for $SRC_DIR using pyenv Python 3.10.4..."
        PYTHONPATH="$(pwd):$PYTHONPATH" $PYENV_PYTHON_EXEC -m lazydocs --src-base-url="https://github.com/NIAGADS/niagads-pylib/blob/main/" --output-path "$OUTPUT_DIR/$SRC_DIR" "$SRC_DIR"
    done
else
    for SRC_DIR in "${SOURCE_DIRS[@]}"
    do
        echo "Generating documentation for $SRC_DIR using Poetry environment..."
        PYTHONPATH="$(pwd):$PYTHONPATH" poetry run lazydocs --src-base-url="https://github.com/NIAGADS/niagads-pylib/blob/main/" --output-path "$OUTPUT_DIR/$SRC_DIR" "$SRC_DIR"
    done
fi


echo "Documentation generation complete. Output saved to $OUTPUT_DIR."
