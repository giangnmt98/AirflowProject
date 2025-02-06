#!/bin/bash

# Hàm hiển thị cách sử dụng script
function usage() {
  echo "Usage: $0 --scenario_path <scenario_path> [--output_dir <output_dir>]"
  exit 1
}

# Gán giá trị mặc định
OUTPUT_DIR="./dags"
CONTROLLER_ID=""
# Xử lý các arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --scenario_path)
      SCENARIO_PATH="$2"
      shift 2
      ;;
    --output_dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      ;;
  esac
done

# Kiểm tra xem SCENARIO_PATH có được cung cấp không
if [ -z "$SCENARIO_PATH" ]; then
  echo "Error: --scenario_path is required."
  usage
fi

# Tạo thư mục output nếu chưa tồn tại
mkdir -p "$OUTPUT_DIR"

# Hàm đọc file YAML và trích xuất thông tin
function extract_yaml_info() {
    python3 << EOF
import yaml
import json

with open("$SCENARIO_PATH", "r") as file:
    try:
        data = yaml.safe_load(file)
    except Exception as e:
        print(f"Failed to parse YAML file: {e}")
        exit(1)

# Xuất thông tin Controller DAG
controller_dag = data.get("controller_dag", {})
sub_dags = controller_dag.get("sub_dags", {})

print(json.dumps({
    "controller_dag": controller_dag,
    "sub_dags": sub_dags
}, indent=2))
EOF
}

# Hàm tạo Controller DAG
function create_controller_dag() {
    local CONTROLLER_INFO=$1
    CONTROLLER_ID=$(echo "$CONTROLLER_INFO" | jq -r '.dag_name')  # Lấy CONTROLLER_ID từ YAML
    if [ -z "$CONTROLLER_ID" ] || [ "$CONTROLLER_ID" == "null" ]; then
        echo "Error: Missing 'dag_name' in 'controller_dag'."
        exit 1
    fi

    local CONTROLLER_FILE_NAME="${CONTROLLER_ID}.py"
    local FILE_NAME="$OUTPUT_DIR/$CONTROLLER_FILE_NAME"
    local SCHEDULE_INTERVAL=$(echo "$CONTROLLER_INFO" | jq -r '.schedule_interval')
    if [[ -z "$SCHEDULE_INTERVAL" || "$SCHEDULE_INTERVAL" == "null" ]]; then
        SCHEDULE_INTERVAL="None"
    else
        SCHEDULE_INTERVAL="\"$SCHEDULE_INTERVAL\""
    fi

    # Tạo Controller DAG
    cat << EOF > "$FILE_NAME"
"""
This module defines a controller DAG for triggering other DAGs dynamically
based on a configuration file provided at runtime. The DAG's configuration
is stored in an external YAML file, and its path is passed as a parameter
to the DAG. The configuration determines which DAGs to trigger and with what
parameters.
"""

from datetime import datetime

import pytz
import yaml
from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.dates import days_ago

from airflowproject.configs import conf

# Constants
CONFIG_FILE_PATH_PARAM = "config_file_path"
TRIGGER_RULE_DONE = "all_done"
POKE_INTERVAL_SEC = 1
TAGS_CONTROLLER = ["controller"]
SCHEDULE_INTERVAL_NONE = None
MAX_ACTIVE_RUNS = 1
CATCHUP = False

@task
def save_dag_run_config(**context):
    """
    Save the configuration file path to XCom.

    This function extracts the configuration file path from the DAG run
    parameters and saves it both to an Airflow Variable and to XCom for
    downstream tasks to access.

    Parameters:
    context (dict): The context dictionary from Airflow containing task
                    and DAG-related metadata.

    Returns:
    None
    """
    # Get DAG parameters from the context
    dag_params = context["dag_run"].conf or {}  # Use .conf for parameters
    config_file_path = dag_params.get(CONFIG_FILE_PATH_PARAM)
    if config_file_path:
        # Save the configuration file path as an Airflow Variable
        Variable.set(CONFIG_FILE_PATH_PARAM, config_file_path)
        # Push the config path to XCom for downstream tasks
        ti = context["ti"]
        ti.xcom_push(key=CONFIG_FILE_PATH_PARAM, value=config_file_path)

@task
def load_dag_configuration(**context):
    """
    Load the DAG configuration from a YAML file.

    This function retrieves the configuration file path from XCom or an
    Airflow Variable, then reads the YAML configuration file to load the
    configuration.

    Parameters:
    context (dict): The context dictionary from Airflow containing task
                    and DAG-related metadata.

    Returns:
    dict: The DAG configuration loaded from the YAML file.

    Raises:
    FileNotFoundError: If the configuration file does not exist.
    yaml.YAMLError: If there is an error in reading the YAML configuration.
    """
    # Access TaskInstance (TI) and pull the config path from XCom
    ti = context["ti"]
    config_file_path = ti.xcom_pull(
        task_ids="save_dag_run_config", key=CONFIG_FILE_PATH_PARAM
    )
    if not config_file_path:
        # Fallback to Airflow Variable if not found in XCom
        config_file_path = Variable.get(CONFIG_FILE_PATH_PARAM)
    # Load the YAML configuration
    with open(config_file_path, "r") as file:
        print(config_file_path)
        dag_info = yaml.safe_load(file)
    # Return the DAG configuration to be available via XCom
    return dag_info

@task
def trigger_dag_tasks(**context):
    """
    Retrieve configuration and trigger DAGs dynamically.

    This function reads the configuration from XCom, iterates over the
    configuration entries, and triggers the respective DAGs dynamically
    using the `TriggerDagRunOperator`.

    Parameters:
    context (dict): The context dictionary from Airflow containing task
                    and DAG-related metadata.

    Returns:
    None

    Raises:
    ValueError: If the configuration is not loaded properly.
    """
    # Retrieve the loaded configuration from XCom
    ti = context["ti"]
    config = ti.xcom_pull(task_ids="load_dag_configuration")
    if not config:
        raise ValueError("Failed to load DAG configuration.")

    local_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    failed_dags = []  # List to track failed DAGs

    for scheduled_dag_id, parameters in config['controller_dag']['sub_dags'].items():
        execution_time = parameters.get("execution_time")
        try:
            # Trigger DAGs dynamically based on the configuration
            if execution_time is None:
                TriggerDagRunOperator(
                    task_id=f"trigger_{scheduled_dag_id}",
                    trigger_dag_id=scheduled_dag_id,
                    conf=parameters.get("params", {}),
                    execution_date=datetime.now(local_tz).strftime(
                        "%Y-%m-%dT%H:%M:%S.%f"
                    ),
                    wait_for_completion=True,
                    poke_interval=POKE_INTERVAL_SEC,
                    trigger_rule=TRIGGER_RULE_DONE,
                    reset_dag_run=True,
                ).execute(context)
            else:
                TriggerDagRunOperator(
                    task_id=f"trigger_{scheduled_dag_id}",
                    trigger_dag_id=scheduled_dag_id,
                    execution_date=execution_time,
                    conf=parameters.get("params", {}),
                    wait_for_completion=True,
                    reset_dag_run=True,
                    poke_interval=POKE_INTERVAL_SEC,
                    trigger_rule=TRIGGER_RULE_DONE,
                ).execute(context)
        except Exception as e:
            # Log the exception and add it to failed DAG list
            ti.log.error(f"Failed to trigger DAG {scheduled_dag_id}: {e}")
            failed_dags.append(scheduled_dag_id)

    # If there are failed DAGs, raise an exception to mark controller_dag as failed
    if failed_dags:
        raise Exception(f"The following DAGs failed: {', '.join(failed_dags)}")

with DAG(
    dag_id="${CONTROLLER_ID}",
    schedule_interval=${SCHEDULE_INTERVAL},
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=TAGS_CONTROLLER,
    params={CONFIG_FILE_PATH_PARAM: "$SCENARIO_PATH"},
) as dag:
    # Dummy start task
    start_task = DummyOperator(task_id="start")
    # Task to save configuration to XCom
    save_config_task = save_dag_run_config()
    # Task to load the configuration
    load_config_task = load_dag_configuration()
    # Task to trigger the DAGs dynamically
    trigger_tasks_task = trigger_dag_tasks()
    # Define dependencies
    start_task >> save_config_task >> load_config_task >> trigger_tasks_task
EOF

    echo -e "\e[32mController DAG created: $FILE_NAME\e[0m"
}

# Hàm tạo các sub-DAGs dựa trên logic từ create_airflow_dag.sh
function create_sub_dags() {
    local SUB_DAGS_INFO=$1
    local SUB_DAGS=$(echo "$SUB_DAGS_INFO" | jq -r 'keys[]')

    for SUB_DAG in $SUB_DAGS; do
        local CONFIG=$(echo "$SUB_DAGS_INFO" | jq -r ".[\"$SUB_DAG\"]")
        local GIT_URL=$(echo "$CONFIG" | jq -r '.params.package.RAW_REPO_URL')
        local FILE_NAME="${SUB_DAG}.py"
        local FULL_PATH="$OUTPUT_DIR/$FILE_NAME"
        local PACKAGE_NAME=$(basename -s .git "$GIT_URL")

        # Tạo sub-DAG
        cat << EOL > "$FULL_PATH"
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflowproject.configs import conf
from airflowproject.functions.dag_functions import submit_job
from airflowproject.functions.task_failure_callback import handle_failure_task

# Define DAG configurations and metadata
dag_id = "${SUB_DAG}"
default_args = conf.RuntimeConfig.DEFAULT_ARGS
schedule_interval = None
catchup = False  # Prevent running missed executions

# Define the DAG using context manager for readability
with DAG(
    dag_id=dag_id,
    default_args=default_args,
    schedule_interval=schedule_interval,
    catchup=catchup,
    tags = ["subdag of ${CONTROLLER_ID}"]
) as dag:
    # Define the task with clear structure
    ${PACKAGE_NAME}_task = PythonOperator(
        task_id="${PACKAGE_NAME}_task",
        python_callable=submit_job,
        on_failure_callback=handle_failure_task,
    )
EOL

        echo -e "\e[32mGenerated sub-DAG: $FULL_PATH\e[0m"
    done
}

# Lấy thông tin từ YAML
PARSED_YAML=$(extract_yaml_info)
CONTROLLER_DAG_INFO=$(echo "$PARSED_YAML" | jq '.controller_dag')
SUB_DAGS_INFO=$(echo "$PARSED_YAML" | jq '.sub_dags')

# Tạo Controller DAG và sub-DAGs
create_controller_dag "$CONTROLLER_DAG_INFO"
create_sub_dags "$SUB_DAGS_INFO"
