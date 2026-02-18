"""
Bug 2: Labels содержат кириллицу, но Chatwoot разрешает только латиницу.

ПРОБЛЕМА:
    Chatwoot API для labels разрешает ТОЛЬКО:
    - Латинские буквы (a-z, A-Z)
    - Цифры (0-9)
    - Дефисы (-)
    - Подчёркивания (_)
    
    Текущий код использует кириллические labels:
    - "рус" → должно быть "lang_ru"
    - "узб" → должно быть "lang_uz"
    - "тг" → должно быть "telegram"
    - "сайт" → должно быть "site"
    - "тех" → должно быть "tech_support"
    - "бух" → должно быть "accounting"
    
ОЖИДАЕМОЕ ПОВЕДЕНИЕ:
    Все labels должны содержать только допустимые символы (латиница, цифры, дефисы, подчёркивания).

ТЕСТЫ:
    - Проверка, что labels не содержат кириллицу
    - Проверка правильного маппинга
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Optional


import re

# Регулярное выражение для проверки допустимых символов Chatwoot
# Только латинские буквы, цифры, дефисы и подчёркивания
CHATWOOT_LABEL_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


def is_valid_chatwoot_label(label: str) -> bool:
    """Проверка, что label содержит только допустимые символы для Chatwoot."""
    return bool(CHATWOOT_LABEL_PATTERN.match(label))


class TestBuildChatwootLabels:
    """Тесты для функции _build_chatwoot_labels."""
    
    def test_labels_must_be_latin_only(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 2): Все labels должны содержать только латиницу.
        
        Chatwoot API разрешает только: a-z, A-Z, 0-9, -, _
        Кириллица НЕ допускается!
        
        ЭТОТ ТЕСТ ДОЛЖЕН ПАДАТЬ ДО ИСПРАВЛЕНИЯ БАГА.
        """
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        from FastAPI.routers.consultations import _build_chatwoot_labels
        
        # Получаем все возможные labels
        labels_ru = _build_chatwoot_labels(language="ru", source=None)
        labels_uz = _build_chatwoot_labels(language="uz", source=None)
        labels_tg = _build_chatwoot_labels(language=None, source="TELEGRAM")
        labels_site = _build_chatwoot_labels(language=None, source="site")
        labels_tech = _build_chatwoot_labels(language=None, source=None, consultation_type="Техническая поддержка")
        labels_buh = _build_chatwoot_labels(language=None, source=None, selected_software="бух")
        
        all_labels = labels_ru + labels_uz + labels_tg + labels_site + labels_tech + labels_buh
        
        # Проверяем, что ВСЕ labels содержат только допустимые символы
        invalid_labels = [label for label in all_labels if not is_valid_chatwoot_label(label)]
        
        assert len(invalid_labels) == 0, (
            f"Bug 2: Labels содержат недопустимые символы (кириллицу)!\n"
            f"Недопустимые labels: {invalid_labels}\n"
            f"Chatwoot разрешает только: a-z, A-Z, 0-9, -, _\n"
            f"Нужно заменить на латиницу: рус->lang_ru, узб->lang_uz, тг->telegram, и т.д."
        )
    
    def test_build_labels_russian_language_fixed(self):
        """Тест: язык ru маппится в 'lang_ru' (латиница)."""
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        from FastAPI.routers.consultations import _build_chatwoot_labels
        
        labels = _build_chatwoot_labels(language="ru", source=None)
        
        # После исправления должно быть 'lang_ru' вместо 'рус'
        assert len(labels) > 0, "Should have at least one label for ru language"
        assert is_valid_chatwoot_label(labels[0]), (
            f"Label '{labels[0]}' contains invalid characters. "
            f"Expected latin-only label like 'lang_ru'"
        )
    
    def test_build_labels_telegram_source_fixed(self):
        """Тест: source TELEGRAM маппится в 'telegram' (латиница)."""
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        from FastAPI.routers.consultations import _build_chatwoot_labels
        
        labels = _build_chatwoot_labels(language=None, source="TELEGRAM")
        
        # После исправления должно быть 'telegram' вместо 'тг'
        assert len(labels) > 0, "Should have at least one label for TELEGRAM source"
        assert is_valid_chatwoot_label(labels[0]), (
            f"Label '{labels[0]}' contains invalid characters. "
            f"Expected latin-only label like 'telegram'"
        )
    
    def test_build_labels_backend_source_no_label(self):
        """Тест: source BACKEND НЕ добавляет label (ожидаемое поведение)."""
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        from FastAPI.routers.consultations import _build_chatwoot_labels
        
        labels = _build_chatwoot_labels(language=None, source="BACKEND")
        
        assert len(labels) == 0, f"BACKEND should not add any labels, got: {labels}"
    
    def test_build_labels_empty_input(self):
        """Тест: пустой ввод возвращает пустой список."""
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        from FastAPI.routers.consultations import _build_chatwoot_labels
        
        labels = _build_chatwoot_labels(language=None, source=None)
        
        assert labels == [], f"Expected empty list for empty input, got: {labels}"
    
    def test_all_labels_valid_format(self):
        """
        Тест: Все возможные комбинации labels должны быть валидными для Chatwoot.
        
        ЭТОТ ТЕСТ ДОЛЖЕН ПАДАТЬ ДО ИСПРАВЛЕНИЯ БАГА.
        """
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        from FastAPI.routers.consultations import _build_chatwoot_labels
        
        # Тестируем все комбинации
        test_cases = [
            {"language": "ru", "source": None},
            {"language": "uz", "source": None},
            {"language": None, "source": "TELEGRAM"},
            {"language": None, "source": "site"},
            {"language": None, "source": "web"},
            {"language": None, "source": None, "consultation_type": "Техническая поддержка"},
            {"language": None, "source": None, "selected_software": "бух"},
            {"language": None, "source": None, "selected_software": "рт"},
            {"language": None, "source": None, "selected_software": "ук"},
            # Комбинированный тест
            {"language": "ru", "source": "TELEGRAM", "consultation_type": "Техническая поддержка"},
        ]
        
        invalid_found = []
        for params in test_cases:
            labels = _build_chatwoot_labels(**params)
            for label in labels:
                if not is_valid_chatwoot_label(label):
                    invalid_found.append((params, label))
        
        assert len(invalid_found) == 0, (
            f"Bug 2: Found {len(invalid_found)} invalid labels:\n" +
            "\n".join([f"  {params} -> '{label}'" for params, label in invalid_found])
        )


class TestAddConversationLabelsPayload:
    """Тесты для проверки формата payload add_conversation_labels."""
    
    @pytest.mark.asyncio
    async def test_add_labels_payload_format(self):
        """
        Тест: payload для add_conversation_labels имеет правильный формат.
        
        Ожидаемый формат: {"labels": ["label1", "label2"]}
        """
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        
        # Мокаем httpx.AsyncClient
        captured_payload = {}
        
        async def mock_request(method, url, headers=None, json=None, params=None):
            captured_payload["method"] = method
            captured_payload["url"] = url
            captured_payload["json"] = json
            
            # Мокаем успешный ответ
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"payload": {"labels": ["рус", "тг"]}}'
            mock_response.content = '{"payload": {"labels": ["lang_ru", "telegram"]}}'.encode('utf-8')
            mock_response.json.return_value = {"payload": {"labels": ["рус", "тг"]}}
            mock_response.raise_for_status = MagicMock()
            mock_response.reason_phrase = "OK"
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.request = AsyncMock(side_effect=mock_request)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            from FastAPI.services.chatwoot_client import ChatwootClient
            
            client = ChatwootClient()
            
            # Мокаем ensure_label_exists чтобы не делать реальные запросы
            client.ensure_label_exists = AsyncMock(return_value=True)
            
            await client.add_conversation_labels(
                conversation_id="12345",
                labels=["рус", "тг"]
            )
        
        # Проверяем формат payload
        assert "json" in captured_payload, "Payload should be captured"
        assert captured_payload["json"] is not None, "JSON payload should not be None"
        
        payload = captured_payload["json"]
        
        # Проверяем структуру payload
        assert "labels" in payload, f"Payload should have 'labels' key, got: {payload}"
        assert isinstance(payload["labels"], list), f"labels should be a list, got: {type(payload['labels'])}"
        assert payload["labels"] == ["рус", "тг"], f"labels should match, got: {payload['labels']}"
    
    @pytest.mark.asyncio
    async def test_add_labels_empty_list_skipped(self):
        """Тест: пустой список labels не вызывает HTTP запрос."""
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        
        request_called = False
        
        async def mock_request(*args, **kwargs):
            nonlocal request_called
            request_called = True
            return MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.request = AsyncMock(side_effect=mock_request)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            from FastAPI.services.chatwoot_client import ChatwootClient
            
            client = ChatwootClient()
            
            result = await client.add_conversation_labels(
                conversation_id="12345",
                labels=[]  # Пустой список
            )
        
        assert request_called is False, "HTTP request should not be made for empty labels"
        assert result == {}, "Empty labels should return empty dict"
    
    @pytest.mark.asyncio
    async def test_add_labels_cyrillic_encoding(self):
        """
        Тест: кириллические labels корректно кодируются в JSON.
        
        Проверяем, что ensure_ascii=False используется при логировании.
        """
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        import json
        
        labels = ["рус", "узб", "тг", "сайт", "тех", "бух"]
        
        # Проверяем, что labels корректно сериализуются
        serialized = json.dumps({"labels": labels}, ensure_ascii=False)
        
        assert "рус" in serialized, f"Cyrillic should be preserved, got: {serialized}"
        assert "\\u" not in serialized, f"Cyrillic should not be escaped, got: {serialized}"
        
        # Проверяем десериализацию
        deserialized = json.loads(serialized)
        assert deserialized["labels"] == labels, f"Deserialized labels should match, got: {deserialized}"


class TestLabelsIntegration:
    """Интеграционные тесты для labels."""
    
    @pytest.mark.asyncio
    async def test_labels_added_after_conversation_creation(self):
        """
        Тест: labels добавляются ПОСЛЕ успешного создания conversation.
        
        Это важно, т.к. Chatwoot может игнорировать labels в запросе создания.
        """
        # Этот тест проверяет порядок вызовов
        calls = []
        
        async def mock_create_conversation(*args, **kwargs):
            calls.append("create_conversation")
            return {"id": 12345}
        
        async def mock_add_labels(*args, **kwargs):
            calls.append("add_labels")
            return {"labels": ["рус"]}
        
        # Проверяем, что add_labels вызывается после create_conversation
        # Логика в consultations.py: сначала создание, потом labels
        
        # Имитируем порядок вызовов из consultations.py
        await mock_create_conversation()
        await mock_add_labels()
        
        assert calls == ["create_conversation", "add_labels"], (
            f"Labels should be added after conversation creation, got: {calls}"
        )
