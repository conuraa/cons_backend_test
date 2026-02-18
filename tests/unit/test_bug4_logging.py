"""
Bug 4: Структурированное логирование с категориями.

ТРЕБОВАНИЯ:
    1. Три категории логгеров:
       - app_logger: бизнес-логика (routers, models, services)
       - integration_logger: интеграции (Chatwoot, 1C, Telegram)
       - system_logger: системные события (scheduler, ETL, errors)
    
    2. Каждый логгер должен:
       - Писать в свой файл (app.log, integration.log, system.log)
       - Использовать структурированный формат (JSON)
       - Включать категорию в запись

ТЕСТЫ:
    - Проверка создания логгеров
    - Проверка категорий в записях
    - Проверка маппинга модулей на категории
"""
import pytest
import logging
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, "/home/sada/cons_backend")


class TestLoggingConfig:
    """Тесты для конфигурации логирования."""
    
    def test_import_logging_config(self):
        """Модуль logging_config должен импортироваться."""
        from FastAPI.utils.logging_config import (
            app_logger,
            integration_logger,
            system_logger
        )
        assert app_logger is not None
        assert integration_logger is not None
        assert system_logger is not None
    
    def test_app_logger_exists(self):
        """app_logger должен существовать."""
        from FastAPI.utils.logging_config import app_logger
        
        # Проверяем что это LoggerAdapter
        assert hasattr(app_logger, "info")
        assert hasattr(app_logger, "error")
        assert hasattr(app_logger, "debug")
        assert hasattr(app_logger, "warning")
    
    def test_integration_logger_exists(self):
        """integration_logger должен существовать."""
        from FastAPI.utils.logging_config import integration_logger
        
        assert hasattr(integration_logger, "info")
        assert hasattr(integration_logger, "error")
    
    def test_system_logger_exists(self):
        """system_logger должен существовать."""
        from FastAPI.utils.logging_config import system_logger
        
        assert hasattr(system_logger, "info")
        assert hasattr(system_logger, "error")


class TestLoggerCategories:
    """Тесты для категорий логгеров."""
    
    def test_app_logger_has_app_category(self, caplog):
        """app_logger должен иметь категорию 'app'."""
        from FastAPI.utils.logging_config import app_logger
        
        with caplog.at_level(logging.INFO):
            app_logger.info("Test message from app")
        
        # Проверяем что запись была создана логгером 'app'
        assert any(record.name == "app" for record in caplog.records), \
            f"Expected logger 'app', got: {[r.name for r in caplog.records]}"
    
    def test_integration_logger_has_integration_category(self, caplog):
        """integration_logger должен иметь категорию 'integration'."""
        from FastAPI.utils.logging_config import integration_logger
        
        with caplog.at_level(logging.INFO):
            integration_logger.info("Test message from integration")
        
        assert any(record.name == "integration" for record in caplog.records), \
            f"Expected logger 'integration', got: {[r.name for r in caplog.records]}"
    
    def test_system_logger_has_system_category(self, caplog):
        """system_logger должен иметь категорию 'system'."""
        from FastAPI.utils.logging_config import system_logger
        
        with caplog.at_level(logging.INFO):
            system_logger.info("Test message from system")
        
        assert any(record.name == "system" for record in caplog.records), \
            f"Expected logger 'system', got: {[r.name for r in caplog.records]}"


class TestModuleToLoggerMapping:
    """Тесты для маппинга модулей на логгеры."""
    
    def test_chatwoot_client_uses_integration(self):
        """chatwoot_client должен использовать integration_logger."""
        from FastAPI.utils.logging_config import get_logger_for_module
        
        logger = get_logger_for_module("FastAPI.services.chatwoot_client")
        
        # Проверяем что это integration логгер
        assert logger.extra.get("category") == "integration", \
            f"chatwoot_client should use integration, got: {logger.extra}"
    
    def test_onec_client_uses_integration(self):
        """onec_client должен использовать integration_logger."""
        from FastAPI.utils.logging_config import get_logger_for_module
        
        logger = get_logger_for_module("FastAPI.services.onec_client")
        
        assert logger.extra.get("category") == "integration"
    
    def test_telegram_bot_uses_integration(self):
        """telegram_bot должен использовать integration_logger."""
        from FastAPI.utils.logging_config import get_logger_for_module
        
        logger = get_logger_for_module("FastAPI.services.telegram_bot")
        
        assert logger.extra.get("category") == "integration"
    
    def test_scheduler_uses_system(self):
        """scheduler должен использовать system_logger."""
        from FastAPI.utils.logging_config import get_logger_for_module
        
        logger = get_logger_for_module("FastAPI.scheduler")
        
        assert logger.extra.get("category") == "system", \
            f"scheduler should use system, got: {logger.extra}"
    
    def test_catalog_scripts_uses_system(self):
        """catalog_scripts должны использовать system_logger."""
        from FastAPI.utils.logging_config import get_logger_for_module
        
        logger = get_logger_for_module("FastAPI.catalog_scripts.pull_cons_cl")
        
        assert logger.extra.get("category") == "system"
    
    def test_routers_use_app(self):
        """routers должны использовать app_logger."""
        from FastAPI.utils.logging_config import get_logger_for_module
        
        logger = get_logger_for_module("FastAPI.routers.consultations")
        
        assert logger.extra.get("category") == "app", \
            f"routers should use app, got: {logger.extra}"
    
    def test_unknown_module_uses_app(self):
        """Неизвестные модули должны использовать app_logger по умолчанию."""
        from FastAPI.utils.logging_config import get_logger_for_module
        
        logger = get_logger_for_module("unknown.module")
        
        assert logger.extra.get("category") == "app"


class TestLoggerHelpers:
    """Тесты для хелперов логгеров."""
    
    def test_get_app_logger_with_module(self):
        """get_app_logger должен включать имя модуля."""
        from FastAPI.utils.logging_config import get_app_logger
        
        logger = get_app_logger("consultations")
        
        assert logger.extra.get("category") == "app"
        assert logger.extra.get("module") == "consultations"
    
    def test_get_integration_logger_with_service(self):
        """get_integration_logger должен включать имя сервиса."""
        from FastAPI.utils.logging_config import get_integration_logger
        
        logger = get_integration_logger("chatwoot")
        
        assert logger.extra.get("category") == "integration"
        assert logger.extra.get("service") == "chatwoot"
    
    def test_get_system_logger_with_component(self):
        """get_system_logger должен включать имя компонента."""
        from FastAPI.utils.logging_config import get_system_logger
        
        logger = get_system_logger("scheduler")
        
        assert logger.extra.get("category") == "system"
        assert logger.extra.get("component") == "scheduler"


class TestLoggingOutput:
    """Тесты для вывода логов."""
    
    def test_app_logger_logs_message(self, caplog):
        """app_logger должен логировать сообщения."""
        from FastAPI.utils.logging_config import app_logger
        
        test_message = "Test consultation created"
        
        with caplog.at_level(logging.INFO):
            app_logger.info(test_message)
        
        assert test_message in caplog.text
    
    def test_integration_logger_logs_message(self, caplog):
        """integration_logger должен логировать сообщения."""
        from FastAPI.utils.logging_config import integration_logger
        
        test_message = "Chatwoot API called"
        
        with caplog.at_level(logging.INFO):
            integration_logger.info(test_message)
        
        assert test_message in caplog.text
    
    def test_system_logger_logs_error(self, caplog):
        """system_logger должен логировать ошибки."""
        from FastAPI.utils.logging_config import system_logger
        
        test_message = "Database connection failed"
        
        with caplog.at_level(logging.ERROR):
            system_logger.error(test_message)
        
        assert test_message in caplog.text
    
    def test_logger_levels(self, caplog):
        """Логгеры должны поддерживать все уровни."""
        from FastAPI.utils.logging_config import app_logger
        
        with caplog.at_level(logging.DEBUG):
            app_logger.debug("Debug message")
            app_logger.info("Info message")
            app_logger.warning("Warning message")
            app_logger.error("Error message")
        
        assert "Debug message" in caplog.text
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text


class TestSetupLogging:
    """Тесты для функции setup_logging."""
    
    def test_setup_logging_creates_logs_dir(self, tmp_path):
        """setup_logging должен создавать директорию для логов."""
        from FastAPI.utils.logging_config import setup_logging
        
        log_dir = tmp_path / "test_logs"
        
        setup_logging(log_dir=str(log_dir))
        
        assert log_dir.exists(), f"Log directory {log_dir} should be created"
    
    def test_setup_logging_configures_level(self, caplog):
        """setup_logging должен настраивать уровень логирования."""
        from FastAPI.utils.logging_config import setup_logging, app_logger
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            setup_logging(log_dir=tmp_dir, level="DEBUG")
            
            with caplog.at_level(logging.DEBUG):
                app_logger.debug("Debug level message")
            
            # Проверяем что DEBUG сообщения логируются
            assert "Debug level message" in caplog.text
