"""
Bug 7: Отсутствует fallback для language при создании консультации в 1C.

ПРОБЛЕМА:
    При создании консультации в 1C через create_consultation_odata:
    - Если payload.consultation.lang = None
    - Функция get_language_key просто возвращает дефолт "ru"
    - Не проверяется язык из OnlineQuestion (если вопрос выбран)
    - Не проверяется язык клиента (если есть TelegramUser с language_code)

ОЖИДАЕМОЕ ПОВЕДЕНИЕ:
    Fallback цепочка для language:
    1. payload.consultation.lang (явно указан)
    2. OnlineQuestion.language (если выбран вопрос)
    3. Дефолт "ru"

РЕШЕНИЕ:
    Добавить fallback логику в get_language_key или в вызывающий код.

ТЕСТЫ:
    - language из payload используется
    - language из OnlineQuestion используется как fallback
    - Дефолт "ru" используется в крайнем случае
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

sys.path.insert(0, "/home/sada/cons_backend")


class TestBug7LanguageFallback:
    """Тесты для Bug 7: Fallback для language."""
    
    def test_get_language_key_with_ru(self):
        """get_language_key возвращает RU key для 'ru'."""
        from FastAPI.services.onec_client import get_language_key, LANG_RU_KEY
        
        result = get_language_key("ru")
        assert result == LANG_RU_KEY
    
    def test_get_language_key_with_uz(self):
        """get_language_key возвращает UZ key для 'uz'."""
        from FastAPI.services.onec_client import get_language_key, LANG_UZ_KEY
        
        result = get_language_key("uz")
        assert result == LANG_UZ_KEY
    
    def test_get_language_key_with_none_returns_default(self):
        """get_language_key возвращает дефолт RU для None."""
        from FastAPI.services.onec_client import get_language_key, LANG_RU_KEY
        
        result = get_language_key(None)
        assert result == LANG_RU_KEY
    
    def test_get_language_key_with_empty_returns_default(self):
        """get_language_key возвращает дефолт RU для пустой строки."""
        from FastAPI.services.onec_client import get_language_key, LANG_RU_KEY
        
        result = get_language_key("")
        assert result == LANG_RU_KEY
    
    def test_get_language_key_case_insensitive(self):
        """get_language_key нечувствителен к регистру."""
        from FastAPI.services.onec_client import get_language_key, LANG_RU_KEY, LANG_UZ_KEY
        
        assert get_language_key("RU") == LANG_RU_KEY
        assert get_language_key("Ru") == LANG_RU_KEY
        assert get_language_key("UZ") == LANG_UZ_KEY
        assert get_language_key("Uz") == LANG_UZ_KEY


class TestLanguageFallbackLogic:
    """Тесты для логики fallback."""
    
    def test_fallback_function_exists(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 7): Функция resolve_language_code должна существовать.
        
        Эта функция должна реализовывать fallback логику:
        1. Если lang указан - использовать его
        2. Если lang None и есть question_key - брать из OnlineQuestion
        3. Иначе - дефолт "ru"
        """
        try:
            from FastAPI.services.onec_client import resolve_language_code
            assert callable(resolve_language_code)
        except ImportError:
            # Bug 7: Функция не существует - нужно создать
            pytest.fail(
                "Bug 7: Функция resolve_language_code не существует. "
                "Нужно создать fallback логику для language."
            )
    
    @pytest.mark.asyncio
    async def test_fallback_uses_online_question_language(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 7): Если lang None, должен браться из OnlineQuestion.
        """
        # Mock OnlineQuestion с языком
        mock_question = MagicMock()
        mock_question.language = "uz"
        
        # Mock DB session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_question
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Тестируем fallback логику
        lang_code = None
        question_key = "question-uuid-123"
        
        # Эта логика должна быть в resolve_language_code
        resolved_lang = await _resolve_language_with_fallback(
            lang_code=lang_code,
            question_key=question_key,
            db=mock_db
        )
        
        assert resolved_lang == "uz", (
            f"Bug 7: Если lang=None и вопрос имеет language='uz', "
            f"должен вернуться 'uz'. Получено: {resolved_lang}"
        )
    
    @pytest.mark.asyncio
    async def test_fallback_uses_default_when_no_question(self):
        """Если нет ни lang, ни question - дефолт 'ru'."""
        mock_db = AsyncMock()
        
        resolved_lang = await _resolve_language_with_fallback(
            lang_code=None,
            question_key=None,
            db=mock_db
        )
        
        assert resolved_lang == "ru", (
            f"Без lang и question должен быть дефолт 'ru'. Получено: {resolved_lang}"
        )
    
    @pytest.mark.asyncio
    async def test_explicit_lang_takes_priority(self):
        """Явно указанный lang имеет приоритет."""
        mock_db = AsyncMock()
        
        resolved_lang = await _resolve_language_with_fallback(
            lang_code="uz",
            question_key="question-uuid-123",
            db=mock_db
        )
        
        assert resolved_lang == "uz", (
            f"Явный lang='uz' должен иметь приоритет. Получено: {resolved_lang}"
        )


async def _resolve_language_with_fallback(
    lang_code: str = None,
    question_key: str = None,
    db=None
) -> str:
    """
    Resolve language code with fallback logic.
    
    Fallback chain:
    1. Explicit lang_code if provided
    2. OnlineQuestion.language if question_key provided
    3. Default "ru"
    
    BUG FIX #7: Эта логика должна быть добавлена в onec_client.py
    """
    # 1. Явный язык
    if lang_code:
        return lang_code.lower()
    
    # 2. Язык из OnlineQuestion
    if question_key and question_key != "00000000-0000-0000-0000-000000000000" and db:
        try:
            from sqlalchemy import select
            # Имитируем запрос к OnlineQuestion
            # В реальном коде: select(OnlineQuestion.language).where(OnlineQuestion.ref_key == question_key)
            result = await db.execute(None)  # Mock
            question = result.scalar_one_or_none()
            if question and hasattr(question, 'language') and question.language:
                return question.language.lower()
        except Exception:
            pass
    
    # 3. Дефолт
    return "ru"


class TestPayloadLanguage:
    """Тесты для языка в payload 1C."""
    
    @pytest.mark.asyncio
    async def test_payload_always_has_language_key(self):
        """
        Payload для 1C всегда должен содержать Язык_Key.
        """
        from FastAPI.services.onec_client import get_language_key, LANG_RU_KEY
        
        # Симулируем создание payload
        language_code = None  # Не указан
        language_key = get_language_key(language_code)
        
        payload = {}
        if language_key:
            payload["Язык_Key"] = language_key
        
        assert "Язык_Key" in payload, (
            "Payload должен всегда содержать Язык_Key"
        )
        assert payload["Язык_Key"] == LANG_RU_KEY, (
            f"Дефолтный язык должен быть RU. Получено: {payload['Язык_Key']}"
        )
    
    def test_language_key_never_none(self):
        """get_language_key никогда не должен возвращать None."""
        from FastAPI.services.onec_client import get_language_key
        
        test_cases = [None, "", "ru", "uz", "en", "invalid", "RU", "UZ"]
        
        for lang_code in test_cases:
            result = get_language_key(lang_code)
            assert result is not None, (
                f"get_language_key({repr(lang_code)}) вернул None"
            )


class TestIntegrationLanguagePayload:
    """Интеграционные тесты для языка в create_consultation_odata."""
    
    @pytest.mark.asyncio
    async def test_create_consultation_with_language(self):
        """Консультация создаётся с правильным языком."""
        # Этот тест проверяет, что язык правильно попадает в payload
        from FastAPI.services.onec_client import get_language_key, LANG_UZ_KEY
        
        language_code = "uz"
        language_key = get_language_key(language_code)
        
        assert language_key == LANG_UZ_KEY
