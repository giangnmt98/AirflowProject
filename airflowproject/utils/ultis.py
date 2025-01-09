"""
This module provides utility functions for sending messages via Telegram
and loading YAML configuration files.
"""

import telebot
import yaml
from telebot.apihelper import ApiException

from airflowproject.configs import conf
from airflowproject.utils.custom_logger import CustomLogger

logger = CustomLogger(name=conf.RuntimeConfig.APP_NAME).get_logger()


def send_tele_message(api_token, group_id, message):
    """
    Send a message to a Telegram group using the Telebot API.

    Args:
        api_token (str): The API token for the Telegram bot.
        group_id (str): The ID of the Telegram group to send the message to.
        message (str): The message content to send, formatted in HTML.
    """
    logger.info("Sending message to Telegram...")
    bot = telebot.TeleBot(api_token)
    try:
        if len(str(message)) > 0:
            bot.send_message(group_id, message, parse_mode="HTML")
            logger.info("Message sent successfully!")
    except ApiException as e:
        bot.send_message(group_id, message)
        logger.error("Failed to send message: %s", e)


def load_yaml_config(file_path: str) -> dict:
    """
    Load YAML config file into a dictionary.

    Args:
        file_path (str): Path to the configuration file.

    Returns:
        dict: Dictionary representation of the configuration.

    Raises:
        ValueError: If the configuration file is not found.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError as exc:
        raise ValueError(f"Configuration file '{file_path}' not found.") from exc
