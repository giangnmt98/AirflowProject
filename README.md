
# Airflow Project

## Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
  - [System Requirements](#system-requirements)
  - [Installation Guide](#installation-guide)
  - [Run Unit Tests](#run-unit-tests)
- [Usage](#usage)
- [Project Directory Structure](#project-directory-structure)

## Introduction

This project is Airflow project template.

## Installation

### System Requirements

- Python >=3.9.18
- Apache Airflow 2.10.2

### Installation Guide

1. Clone the repository:

```bash
git clone https://github.com/giangnmt98/AirflowProject.git
cd AirflowProject
```

2. Install the required dependencies:

```bash
make venv
```
3. Set up the environment:

   ```bash
   chmod +x set_env_variables.sh
   . set_env_variables.sh
   ```

4. Initialize the Airflow environment:

   ```bash
   airflow db migrate
   airflow users create \
       --username admin \
       --firstname Admin \
       --lastname User \
       --role Admin \
       --email admin@example.com
   ```
### Run Tests
```bash
make test
```
### Run pre-commit checks
```bash
chmod +x check_before_commit.sh
./check_before_commit.sh
```

### Run styling
```bash
make style
```

## Usage

1. Start the Airflow scheduler:

   ```bash
   airflow scheduler
   ```

2. Start the Airflow web server:

   ```bash
   airflow webserver --port 8080
   ```

3. Access the Airflow UI at [http://localhost:8080](http://localhost:8080).

## Project Directory Structure

```
vnpt_ic_mytv_airflow/
├── .github/
│   └── workflows/
│       └── project_ci.yaml
├── airflowproject/  # Airflow home directory
│   ├── configs/
│   │   ├── airflow.cfg
│   │   └── conf.py
│   ├── dags/
│   │   ├── dag1.py
│   │   ├── dag2.py
│   │   └── __init__.py
│   ├── functions/
│   │   ├── custom_operator.py
│   │   └── custom_sensor.py
│   │   └── __init__.py
│   ├── utils/
│   │   └── custom_util.py
│   │   └── __init__.py
│   └── tests/  # Unit tests for the project
│       └── __init__.py
│
├── example_config # Example configuration files
│
├── airflow_scheduler.sh
├── airflow_webserver.sh
├── pyproject.toml
├── requirements.txt
├── set_env_variables.sh
├── check_before_commit.sh
└── README.md
```

### Folder and File Descriptions

- **.github/workflows/**: Contains GitHub Actions workflows for CI/CD.
- **airflowproject/**: The Airflow home directory containing configurations, DAGs, and plugins.
- **airflowproject/dags/**: Contains the Directed Acyclic Graphs (DAGs) for the project.
- **airflowproject/functions/**: Contains decoupled Python logic for the recommendation system.
- **airflowproject/tests/**: Includes unit tests for Python functions and DAG integrity.
- **airflowproject/utils/**: Contains utility functions for the project.\
- **example_config/**: Contains example configuration files.
- **pyproject.toml**: Python project configuration file.
- **requirements.txt**: List of project dependencies.
- **set_env_variables.sh**: Script for setting up environment variables.
- **check_before_commit.sh**: Scripts to check before commit.
- **airflow_webserver.sh**: Script for running Airflow Web UI.
- **airflow_scheduler.sh**: Script for running Airflow Scheduler.
- **README.md**: Project documentation.