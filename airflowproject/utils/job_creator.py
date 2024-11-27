"""
Module for setting up and executing a package environment using a bash script.
"""

import os
import tempfile

from airflowproject.utils.ultis import load_yaml_config


class JobCreator:
    """
    A class to create and manage job execution environments using bash scripts.
    """

    def __init__(self, config):
        """
        Initialize the PackageSetup class with the given configuration path.

        Args:
            config: Job config
        """
        self.config = config
        print(config)
        self.repo_url = self._construct_repo_url()
        print(self.repo_url)
        self.venv_name = self._construct_venv_name()
        self.full_venv_path = self._construct_full_venv_path()
        self.repo_dir = self._construct_repo_dir()

    def _construct_repo_url(self) -> str:
        raw_repo_url = self.config["RAW_REPO_URL"]
        package_host = f"github_{self.config['PACKAGE_NAME']}_host"
        return raw_repo_url.replace("github.com", package_host)

    def _construct_venv_name(self) -> str:
        return f"{self.config['PACKAGE_NAME']}_{self.config['PACKAGE_VERSION']}_venv"

    def _construct_full_venv_path(self) -> str:
        return os.path.join(self.config["VENV_HUB_PATH"], self.venv_name)

    def _construct_repo_dir(self) -> str:
        return f"$(basename {self.config['RAW_REPO_URL']} .git)"

    def save_script_to_tmp_file(
        self, script_content: str, dir_path: str = "/tmp"
    ) -> str:
        """
        Save the generated bash script to a temporary file.

        Args:
            script_content (str): Content of the bash script.
            dir_path (str): Directory path to save the temporary file.

        Returns:
            str: Path to the temporary file.

        Raises:
            IOError: If the script cannot be saved.
        """
        try:
            with tempfile.NamedTemporaryFile(
                "w", delete=False, suffix=".sh", dir=dir_path
            ) as tmp_file:
                tmp_file.write(script_content)
                os.chmod(tmp_file.name, 0o755)
                return tmp_file.name
        except Exception as e:
            raise IOError(f"Failed to save script: {e}") from e

    def generate_bash_script(self) -> str:
        """
        Generate the complete bash script combining all the sections.

        Returns:
            str: Complete bash script.
        """
        return f"""#!/bin/bash
    set -e
    # Set up a trap to clean up on exit
    trap 'cleanup; exit' EXIT
    # Define color codes for output messages
    RED='\\033[0;31m'
    GREEN='\\033[0;32m'
    YELLOW='\\033[1;33m'
    BLUE='\\033[0;34m'
    NC='\\033[0m'

    # Function to log errors and exit
    log_error() {{
        echo -e "${{RED}}[ERROR] $1${{NC}}" >&2
        exit 1
    }}

    # Function to print a separator line
    separator() {{
        printf '=%.0s' {{1..40}}
        echo ""
    }}

    # Function to clean up after execution
    cleanup() {{
        echo -e "${{YELLOW}}Cleaning up...${{NC}}"
        cd .. && rm -rf {self.repo_dir} || \\
        log_error "Cleanup failed: Unable to remove directory '{self.repo_dir}'. \\
        Check if the directory exists and has correct permissions."
        separator
    }}

    # Start script execution
    echo -e "${{BLUE}}Starting script execution...${{NC}}"
    separator

    # Step 1: Get the package from the git repository
    echo -e "${{YELLOW}}Cloning repository...${{NC}}"
    git clone --branch {self.config['PACKAGE_VERSION']} --depth 1 \\
        {self.repo_url} > /dev/null 2>&1 || 
        log_error "
        Failed to clone repository from '{self.repo_url}' with tag '{self.config['PACKAGE_VERSION']}'. 
        Check the repository URL and network."

    cd {self.repo_dir} || \\
        log_error "Failed to change directory to '{self.repo_dir}'. \\
        Make sure the repository was cloned successfully."
    separator

    # Step 2: Set up the Python environment
    echo -e "${{YELLOW}}Setting up Python environment...${{NC}}"
    if [ ! -d "{self.full_venv_path}" ]; then
        echo -e "${{YELLOW}}Creating a new environment at \\
        {self.full_venv_path}.${{NC}}"
        python{self.config['PYTHON_VERSION']} -m venv \\
            "{self.full_venv_path}" || \\
            log_error "Failed to create virtual environment at \\
            '{self.full_venv_path}' using Python \\
            {self.config['PYTHON_VERSION']}. Verify Python installation."
    fi

    # Activate the virtual environment
    . "{self.full_venv_path}/bin/activate" || \\
        log_error "Failed to activate virtual environment at \\
        '{self.full_venv_path}/bin/activate'. Check if it was created correctly."

    # Upgrade pip, setuptools, and wheel
    echo -e "${{YELLOW}}Upgrading pip, setuptools, and wheel...${{NC}}"
    python3 -m pip install --upgrade -q pip setuptools wheel || \\
        log_error "Failed to upgrade pip, setuptools, or wheel. \\
        Verify network connection or repository availability."

    # Install project dependencies
    echo -e "${{YELLOW}}Installing project dependencies...${{NC}}"
    python3 -m pip install -q -e . || \\
        log_error "Failed to install the package dependencies. Check 'setup.py' \\
        or 'requirements.txt' for missing dependencies or errors."
    separator

    # Step 3: Run the package
    echo -e "${{YELLOW}}Running the package...${{NC}}"
    python3 "{self.config['PACKAGE_NAME']}/main.py" --config_path \\
        "{self.config['CONFIG_PATH']}" || \\
        log_error "Failed to run the package '{self.config['PACKAGE_NAME']}'. \\
        Verify the config file at '{self.config['CONFIG_PATH']}'."
    separator

    # Completion message
    echo -e "${{GREEN}}Script execution completed successfully.${{NC}}"
    separator
    """
