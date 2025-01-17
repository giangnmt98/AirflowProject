# Shell used for executing scripts
SHELL := /bin/bash

# Configuration
# Alias for Python executable
PYTHON_EXEC := python3

# Virtual environment directory
VENV_DIR := airflowproject_env

# Directory for storing processed data
CODE_DIRECTORY := airflowproject

# Directory containing tests
TEST_DIRECTORY := airflowproject/tests

# Virtual environment setup
venv:
	# Creates the virtual environment and installs dependencies
	$(PYTHON_EXEC) -m venv $(VENV_DIR) && \
	source $(VENV_DIR)/bin/activate && \
	$(PYTHON_EXEC) -m pip install --upgrade pip setuptools wheel && \
	$(PYTHON_EXEC) -m pip install -e .[dev]

# Code styling
style:
	# Formats the code with Black
	black ./$(CODE_DIRECTORY)
	# Checks the code style using Flake8
	flake8 ./$(CODE_DIRECTORY)
	# Sorts the imports using isort
	isort -rc ./$(CODE_DIRECTORY)
	pylint ./$(CODE_DIRECTORY)

test:
	# Run script check before commit
	chmod +x run_check.sh
	./run_check.sh check_change_line

.PHONY: venv style test