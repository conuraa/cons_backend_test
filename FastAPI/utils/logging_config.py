"""
BUG FIX #4: Централизованная конфигурация логирования.

Три категории логгеров:
- app_logger: бизнес-логика (консультации, клиенты)
- integration_logger: внешние интеграции (Chatwoot, 1C, Telegram)
- system_logger: системные события (ошибки, ETL)
"""
import logging
import logging.config
from typing import Dict, Any, Optional
import os
import json
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """Форматтер для JSON логов (production)"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Форматтер для консольного вывода (dev)"""
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "()": ConsoleFormatter,
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "structured": {
            "()": StructuredFormatter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "stream": "ext://sys.stdout",
        },
        "file_app": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "structured",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "file_integration": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "structured",
            "filename": "logs/integration.log",
            "maxBytes": 10485760,
            "backupCount": 5,
        },
        "file_system": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "structured",
            "filename": "logs/system.log",
            "maxBytes": 10485760,
            "backupCount": 5,
        },
    },
    "loggers": {
        "app": {
            "level": "DEBUG",
            "handlers": ["console", "file_app"],
            "propagate": False,
        },
        "integration": {
            "level": "DEBUG",
            "handlers": ["console", "file_integration"],
            "propagate": False,
        },
        "system": {
            "level": "DEBUG",
            "handlers": ["console", "file_system"],
            "propagate": False,
        },
        "httpx": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}


def setup_logging(log_dir: str = "logs"):
    """Инициализация системы логирования"""
    os.makedirs(log_dir, exist_ok=True)
    
    # Обновляем пути к файлам
    for handler_name in ["file_app", "file_integration", "file_system"]:
        if handler_name in LOGGING_CONFIG["handlers"]:
            filename = LOGGING_CONFIG["handlers"][handler_name]["filename"]
            LOGGING_CONFIG["handlers"][handler_name]["filename"] = os.path.join(
                log_dir, os.path.basename(filename)
            )
    
    logging.config.dictConfig(LOGGING_CONFIG)


class CategoryLoggerAdapter(logging.LoggerAdapter):
    """Адаптер для добавления контекста к логам"""
    
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def _create_logger(name: str, category: str) -> logging.LoggerAdapter:
    """Создать логгер с категорией"""
    logger = logging.getLogger(name)
    return CategoryLoggerAdapter(logger, {"category": category})


# Готовые логгеры для использования
app_logger = _create_logger("app", "app")
integration_logger = _create_logger("integration", "integration")
system_logger = _create_logger("system", "system")


def get_logger_for_module(module_name: str) -> logging.LoggerAdapter:
    """
    Получить подходящий логгер по имени модуля.
    
    Примеры:
        get_logger_for_module("chatwoot_client") -> integration_logger
        get_logger_for_module("consultations") -> app_logger
        get_logger_for_module("scheduler") -> system_logger
    """
    module_lower = module_name.lower()
    
    # Интеграции
    if any(x in module_lower for x in ["chatwoot", "onec", "1c", "telegram", "httpx"]):
        return integration_logger
    
    # Системные
    if any(x in module_lower for x in ["scheduler", "etl", "pull_", "sync_", "error"]):
        return system_logger
    
    # По умолчанию - app
    return app_logger
