"""
Module for handling task failures in Airflow.
"""

import time
from typing import Any, Callable, Dict, Optional, Tuple

from airflow.utils.state import State
from pytz import timezone

from airflowproject.configs import conf
from airflowproject.utils.custom_logger import CustomLogger
from airflowproject.utils.ultis import send_tele_message

# Initialize the logger with the application name
logger = CustomLogger(name=conf.RuntimeConfig.APP_NAME).get_logger()


def create_notify_message(
    context: Dict[str, Any], custom_message: Optional[str] = None
) -> str:
    """
    Create a notification message based on the task context.

    Args:
        context (Dict[str, Any]): The task context containing metadata and state.
        custom_message (Optional[str]): A custom message to use instead of
                                        the default message.

    Returns:
        str: The generated notification message.

    Exceptions:
        This function does not raise any exceptions.
    """
    # Extract task instance from the context
    task_instance = context["task_instance"]

    # Convert task start time to 'Asia/Ho_Chi_Minh' timezone
    hcm_start_date = task_instance.start_date.astimezone(
        timezone("Asia/Ho_Chi_Minh")
    ).strftime("%Y-%m-%d %H:%M:%S")

    # Extract the exception message from the context or use a default value
    exception_msg = str(context.get("exception", "Unknown Exception"))

    # Log the exception message
    logger.info("Exception Message: %s", exception_msg)

    # Return the custom message or generate a default message
    return custom_message or (
        f"The task <b>{task_instance.task_id}</b> "
        f"in the DAG <b>{task_instance.dag_id}</b> "
        f"failed, starting at <b>{hcm_start_date}</b>, with an exception:\n"
        f"<code>{exception_msg}</code>"
    )


def extract_telegram_info(notify_config: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """
    Extract TELEGRAM_CHAT_ID and TELEGRAM_TOKEN from config if available.

    Args:
        notify_config (Dict[str, Any]): Notification configuration containing
                                        credential parameters.

    Returns:
        Optional[Tuple[str, str]]: A tuple of (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
                                   if both are available, otherwise None.

    Exceptions:
        This function does not raise any exceptions.
    """
    return (
        (notify_config["TELEGRAM_TOKEN"], notify_config["TELEGRAM_CHAT_ID"])
        if all(key in notify_config for key in ["TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"])
        else None
    )


def retry_task(
    context: Dict[str, Any],
    retries: int,
    delay: int,
    task_function: Callable,
    *args,
    **kwargs,
) -> bool:
    """
    Retry a task function a specified number of times with exponential backoff.

    Args:
        context (Dict[str, Any]): The task context.
        retries (int): The number of times to retry the task.
        delay (int): The initial delay between retries in seconds.
        task_function (Callable): The task function to be retried.
        *args: Arguments passed to the task function.
        **kwargs: Keyword arguments passed to the task function.

    Returns:
        bool: True if the task function succeeds within the given retries,
              otherwise False.

    Exceptions:
        This function handles and logs exceptions raised by the task_function.
    """
    ti = context["task_instance"]

    for attempt in range(1, retries + 1):
        try:
            logger.info("Attempt %d/%d for task %s", attempt, retries, ti.task_id)
            if task_function(*args, **kwargs):
                logger.info("Task %s succeeded on attempt %d.", ti.task_id, attempt)
                return True
        except KeyError as e:
            logger.error("KeyError occurred: %s", e)
        except Exception as e:
            logger.error("Attempt %d failed for task %s: %s", attempt, ti.task_id, e)
            if attempt < retries:
                sleep_time = delay * (2 ** (attempt - 1))
                logger.info("Retrying in %d seconds...", sleep_time)
                time.sleep(sleep_time)
            else:
                logger.error("All %d retry attempts failed.", retries)
    return False


def handle_telegram_notification(
    context: Dict[str, Any],
    notify_config: Dict[str, Any],
    custom_message: Optional[str] = None,
):
    """
    Send a Telegram notification if credentials are available.

    Args:
        context (Dict[str, Any]): The task context.
        notify_config (Dict[str, Any]): Notification configuration containing
                                        Telegram credentials.
        custom_message (Optional[str]): A custom message to use instead of the
                                        default message.

    Exceptions:
        This function does not raise any exceptions.
    """
    # Extract Telegram token and chat ID from the notify configuration
    telegram_info = extract_telegram_info(notify_config)
    if telegram_info:
        token, chat_id = telegram_info

        # Send the notification message via Telegram
        send_tele_message(
            api_token=token,
            group_id=chat_id,
            message=create_notify_message(context, custom_message),
        )


def handle_task_retry(context: Dict[str, Any], retry_config: Dict[str, Any]) -> bool:
    """
    Retry the task based on the retry configuration.

    Args:
        context (Dict[str, Any]): The task context.
        retry_config (Dict[str, Any]): Configuration dict with 'retries' and
                                       'retry_delay' keys.

    Returns:
        bool: True if the task is successfully retried, otherwise False.

    Exceptions:
        This function does not raise any exceptions.
    """
    return retry_task(
        context,
        retries=retry_config.get("retries", 3),
        delay=retry_config.get("retry_delay", 60),
        task_function=context["task_instance"].run,
    )


def handle_failure_task(context: Dict[str, Any], custom_message: Optional[str] = None):
    """
    Callback to handle task failure by retrying or sending notifications.

    Args:
        context (Dict[str, Any]): The context in which the task failed.
        custom_message (Optional[str]): A custom message for the notification.

    Tasks:
        - Retry the failed task based on the retry configuration.
        - Send a Telegram notification if credentials are available.

    Exceptions:
        Raises an exception if the task fails after all retries.
    """
    config = context["dag_run"].conf
    task_instance = context["task_instance"]
    retry_config = config.get("task_failure_callback", {}).get("retry_task")
    notify_config = config.get("task_failure_callback", {}).get("notify")

    try:
        # Handle task retries if configured
        if retry_config and handle_task_retry(context, retry_config):
            logger.info("Task %s retried successfully.", task_instance.task_id)
            return

        # Handle notification if configured
        if notify_config:
            handle_telegram_notification(context, notify_config, custom_message)

        # Mark the task as failed
        task_instance.set_state(State.FAILED)
        logger.error("Task %s marked as FAILED.", task_instance.task_id)
        raise RuntimeError(f"Task {task_instance.task_id} failed after retries.")

    except Exception as e:
        # Log the exception and set task state to FAILED
        logger.exception("Error handling task failure.")
        task_instance.set_state(State.FAILED)
        raise RuntimeError("Task failure handling encountered an error.") from e
