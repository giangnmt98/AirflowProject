"""
This module contains classes and functions for handling runtime configurations,
scheduling configurations, and notifications for an Airflow setup.
"""

from airflow.utils.dates import days_ago
from pendulum import duration


class RuntimeConfig:
    """
    This inner class holds runtime configurations.
    """

    # airflow default args
    APP_NAME = "Airflow Project Template"
    DEFAULT_ARGS = {
        "owner": "airflow",
        "retries": 0,
        "retry_exponential_backoff": True,
        "max_retry_delay": duration(minutes=1),
        "start_date": days_ago(1),
    }


class ScheduleConfig:
    """
    This inner class holds scheduling configurations with more readable names.
    """

    CONTROLLER_DAG_SCHEDULE = "0 8 * * *"  # Transform data at 8:00 AM daily
