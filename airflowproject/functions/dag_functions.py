"""
This module contains functions to set up logging, create log directories,
and manage the submission and logging of subprocess jobs in an Airflow DAG.
"""

import logging
import os
import re
import subprocess

from airflow.exceptions import AirflowException

from airflowproject.utils.job_creator import JobCreator

# Constants
AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "")
LOG_FORMAT = "%(asctime)s - %(message)s"
ANSI_ESCAPE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
LOG_DIR_TEMPLATE = "logs/dag_id={dag_id}/{run_id}/{task_id}"


def setup_logger(
    name: str, log_file: str, level: int = logging.INFO, log_format: str = LOG_FORMAT
) -> logging.Logger:
    """
    Set up a logger for the given name and file.

    Args:
        name (str): Name of the logger.
        log_file (str): File path for the log file.
        level (int, optional): Logging level. Defaults to logging.INFO.
        log_format (str, optional): Logging format. Defaults to LOG_FORMAT.

    Returns:
        logging.Logger: Configured logger object.

    Raises:
        IOError: If there is an issue creating the log file.
    """
    logger = logging.getLogger(name)

    # Clear existing handlers if any
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a file handler and set the formatter
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter(log_format))

    # Add handler to the logger
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger


def create_log_dir(dag_id: str, run_id: str, task_id: str, try_number: int) -> str:
    """
    Create the logging directory for a specific DAG, run, and task.

    Args:
        dag_id (str): The DAG ID.
        run_id (str): The run ID.
        task_id (str): The task ID.
        try_number (int): The try number.

    Returns:
        str: The path of the created log directory.
    """

    # Construct the log directory path
    log_dir = os.path.join(
        AIRFLOW_HOME,
        LOG_DIR_TEMPLATE.format(
            dag_id=dag_id, run_id=run_id, task_id=task_id, try_number=try_number
        ),
    )

    # Create the directory, if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    return log_dir


def initialize_logger(log_dir: str, try_number: int) -> logging.Logger:
    """
    Initialize the logger for a specific try number within a log directory.

    Args:
        log_dir (str): The directory for the log files.
        try_number (int): The attempt number for the log file.

    Returns:
        logging.Logger: Configured logger object.
    """
    return setup_logger(
        "sh_logger",
        os.path.join(log_dir, f"run_script_try_number={try_number}.log"),
        log_format="%(message)s",
    )


def log_subprocess_output(process: subprocess.Popen, logger: logging.Logger) -> str:
    """
    Log the output and errors from a subprocess and return the stderr output.

    Args:
        process (subprocess.Popen): Subprocess whose output needs to be logged.
        logger (logging.Logger): Logger to log the subprocess output.

    Returns:
        str: The captured stderr output.
    """

    # Read stdout and stderr simultaneously to avoid deadlocks
    stdout, stderr = process.communicate()

    # Log the stdout
    for line in stdout.splitlines():
        clean_line = ANSI_ESCAPE.sub("", line.strip())  # Strip ANSI escape codes
        logger.info(clean_line)

    # Log the stderr and prepare the return data
    stderr_output = []
    for line in stderr.splitlines():
        clean_line = ANSI_ESCAPE.sub("", line.strip())  # Strip ANSI escape codes
        stderr_output.append(clean_line)
        if any(keyword in clean_line.lower() for keyword in ["error", "failed"]):
            logger.error(clean_line)
        else:
            logger.info(clean_line)

    return "\n".join(stderr_output)


def submit_job(**context) -> None:
    """
    Submit a job and handle its logging within an Airflow context.

    Args:
        **context: Airflow context.

    Raises:
        AirflowException: If the subprocess fails.
    """

    run_id = context["dag_run"].run_id
    dag_run_conf = context["dag_run"].conf
    dag_id = context["dag"].dag_id
    task_id = context["task"].task_id
    try_number = context["ti"].try_number

    # Create log directory and initialize logger
    log_dir = create_log_dir(dag_id, run_id, task_id, try_number)
    sh_logger = initialize_logger(log_dir, try_number)

    # Log the start of script execution
    sh_logger.info(
        "============================================================================"
    )
    sh_logger.info("Starting script execution...")

    # Set up and execute subprocess
    job_creator = JobCreator(dag_run_conf.get("module_config_path"))
    bash_script = job_creator.generate_bash_script()

    try:
        with subprocess.Popen(
            bash_script,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:

            # Read and log subprocess output
            stderr_output = log_subprocess_output(process, sh_logger)

            # Check the process exit code
            if process.returncode != 0:
                raise AirflowException(f"Subprocess failed with error: {stderr_output}")
    except subprocess.CalledProcessError as e:
        sh_logger.error("Subprocess error: %s", e)
        raise
    except IOError as e:
        sh_logger.error("IOError: $%s", e)
        raise
    try:
        # Save the script to a temporary file and log its path
        tmp_file_path = job_creator.save_script_to_tmp_file(
            script_content=bash_script, dir_path=log_dir
        )
        sh_logger.info("Bash script saved to: %s", tmp_file_path)
    except IOError as e:
        # Log an error if there is an issue saving the script
        sh_logger.error("Error: %s", e)
