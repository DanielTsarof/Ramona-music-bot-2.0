import sys
from typing import Literal

from app.config import config
from loguru import logger
from pydantic import BaseModel


class Logger(BaseModel):
    """
    :param file_path: path to log file
    :param format: log format ("{time} | {level} | {message} | {extra} | {user} | {ip}")
    :param rotation: max log file size ("50 KB, "100 MB" etc.)
    :param enqueue: queue log messages (for multiprocessor and asynchronous programs)
    :param serialize: write log in JSON format
    :param level: log level
    """

    file_path: str = './logs.log'
    format: str = '{time} | {level} | {name}:{function}:{line} | {message}'
    rotation: str = '50 MB'
    enqueue: bool = True
    serialize: bool = True
    level: Literal['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE']


def setup_logger(logger_config: Logger):
    """Function to configure logger

    Parameters
    ----------
    logger_config : LogConfig, optional
        config class for logger setup, by default config.logger
    """

    is_debug = logger_config.level == 'DEBUG'

    # Remove existing loggers to prevent log duplication
    logger.remove()

    # File handler
    logger.add(
        logger_config.file_path,
        format=logger_config.format,
        rotation=logger_config.rotation,
        enqueue=logger_config.enqueue,
        serialize=logger_config.serialize,
        level=logger_config.level,
        backtrace=is_debug,
        diagnose=is_debug,
    )

    # Stdout handler
    logger.add(
        sys.stderr,
        format=logger_config.format,
        enqueue=logger_config.enqueue,
        level=logger_config.level,
        backtrace=is_debug,
        diagnose=is_debug,
        colorize=True,
    )
    return logger


log_config = Logger(file_path=config.LOG_PATH, format=config.LOG_FORMAT, level=config.LOG_LEVEL)

log = setup_logger(logger_config=log_config)
