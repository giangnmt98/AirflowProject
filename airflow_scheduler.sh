#!/bin/bash
. airflowproject_env/bin/activate
chmod +x set_env_variables.sh
./set_env_variables.sh
# Set the database username for MYSQL Database
export MYSQL_USER=root
# Set the database password for MYSQL Database
export MYSQL_PASSWORD=DsteamIC2024
# Set the database host for MYSQL Database
export MYSQL_HOST=0.0.0.0
# Set the database port for MYSQL Database
export MYSQL_PORT=3306
# Set the database name for MYSQL Database
export MYSQL_DATABASE=mytv_dashboard_test
# Set the database name for Airflow database in MySQL
export MYSQL_AIRFLOW_DATABASE=airflowdb_test
# Set the home directory for the custom app
export AIRFLOW_HOME=./airflowproject
# Set the configuration file path for the custom app
export AIRFLOW_CONFIG=$AIRFLOW_HOME/configs/airflow.cfg
# Set Redis password
export REDIS_PASSWORD=DsteamIC2024
# Set MLflow database
export MYSQL_MLFLOW_DATABASE=mlflow
# Run Airflow scheduler
airflow scheduler

