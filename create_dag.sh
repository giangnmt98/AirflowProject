#!/bin/bash

# Initialize variables
DAG_ID=""
OUTPUT_FILE=""
GIT_URL=""

# Function to display usage
usage() {
    echo "Usage: $0 --dag_id <dag_id> --file_path <output_python_file_define_dag (must be in the dags folder)> --git_url <url>"
    echo "Example: $0 --dag_id example_dag --file_path /path/to/dags/example_dag.py --git_url https://github.com/username/repo.git"
    exit 1
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dag_id) DAG_ID="$2"; shift ;;
        --file_path) OUTPUT_FILE="$2"; shift ;;
        --git_url) GIT_URL="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; usage ;;
    esac
    shift
done

# Check if all arguments are provided
if [ -z "$DAG_ID" ] || [ -z "$OUTPUT_FILE" ] || [ -z "$GIT_URL" ]; then
    usage
fi

# Extract package name from Git URL
package_name=$(basename -s .git "$GIT_URL")

# Create the Python file content with the provided DAG ID
cat <<EOL > "$OUTPUT_FILE"
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflowproject.configs import conf
from airflowproject.functions.dag_functions import submit_job
from airflowproject.functions.task_failure_callback import handle_failure_task

# Define DAG configurations and metadata
dag_id = "${DAG_ID}"
default_args = conf.RuntimeConfig.DEFAULT_ARGS
schedule_interval = None
catchup = False  # Prevent running missed executions

# Define the DAG using context manager for readability
with DAG(
    dag_id=dag_id,
    default_args=default_args,
    schedule_interval=schedule_interval,
    catchup=catchup,
) as dag:
    # Define the task with clear structure
    ${package_name}_task = PythonOperator(
        task_id="${package_name}_task",
        python_callable=submit_job,
        on_failure_callback=handle_failure_task,
    )
EOL

echo "DAG file ${OUTPUT_FILE} created successfully with dag_id ${DAG_ID}"