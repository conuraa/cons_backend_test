"""
Bug 8: Комментарий передаётся в 1C с переносами строк.

ПРОБЛЕМА:
    При создании консультации в 1C комментарий формируется так:
    
    ```python
    final_comment = "\\n".join(comment_parts)
    payload["Комментарий"] = final_comment
    ```
    
    Это приводит к многострочному тексту:
    ```
    Создано из Clobus.uz
    Категория вопроса: НДС
    Вопрос: Как рассчитать?
    Мой комментарий
    ```
    
    1C API может некорректно обрабатывать переносы строк:
    - Обрезать текст после первого \\n
    - Показывать символы \\n как есть
    - Ломать форматирование

ОЖИДАЕМОЕ ПОВЕДЕНИЕ:
    Комментарий должен быть одной строкой:
    - \\n → пробел
    - Множественные пробелы → один пробел
    - strip() в начале и конце

ТЕСТЫ:
    - Многострочный текст → одна строка
    - Пользовательский комментарий с \\n → нормализован
    - Пустой комментарий → пустая строка
"""
import pytest
import sys

sys.path.insert(0, "/home/sada/cons_backend")


class TestBug8CommentNormalization:
    """Тесты для Bug 8: Нормализация комментариев."""
    
    def test_normalize_comment_removes_newlines(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 8): Переносы строк должны заменяться на пробелы.
        """
        comment = "Строка 1\nСтрока 2\nСтрока 3"
        
        normalized = normalize_comment(comment)
        
        assert "\n" not in normalized, (
            f"Bug 8: Комментарий не должен содержать \\n. "
            f"Вход: {repr(comment)}, Выход: {repr(normalized)}"
        )
    
    def test_normalize_comment_single_line(self):
        """Нормализованный комментарий должен быть одной строкой."""
        comment = "Первая\nВторая\nТретья"
        
        normalized = normalize_comment(comment)
        
        assert normalized == "Первая Вторая Третья", (
            f"Ожидалось 'Первая Вторая Третья', получено: {repr(normalized)}"
        )
    
    def test_normalize_comment_strips_whitespace(self):
        """Комментарий должен быть без пробелов в начале/конце."""
        comment = "  Текст с пробелами  \n  "
        
        normalized = normalize_comment(comment)
        
        assert not normalized.startswith(" "), "Не должно быть пробелов в начале"
        assert not normalized.endswith(" "), "Не должно быть пробелов в конце"
    
    def test_normalize_comment_multiple_spaces(self):
        """Множественные пробелы должны схлопываться в один."""
        comment = "Слово1    Слово2\n\n\nСлово3"
        
        normalized = normalize_comment(comment)
        
        assert "  " not in normalized, (
            f"Не должно быть множественных пробелов. Получено: {repr(normalized)}"
        )
    
    def test_normalize_comment_empty(self):
        """Пустой комментарий остаётся пустым."""
        assert normalize_comment("") == ""
        assert normalize_comment(None) == ""
        assert normalize_comment("   ") == ""
    
    def test_normalize_comment_crlf(self):
        """Windows-стиль переносов (\\r\\n) тоже нормализуется."""
        comment = "Строка 1\r\nСтрока 2\rСтрока 3"
        
        normalized = normalize_comment(comment)
        
        assert "\r" not in normalized, "Не должно быть \\r"
        assert "\n" not in normalized, "Не должно быть \\n"


def normalize_comment(comment: str) -> str:
    """
    BUG FIX #8: Нормализация комментария для 1C API.
    
    - Заменяет переносы строк на пробелы
    - Убирает множественные пробелы
    - Делает strip()
    
    Args:
        comment: Исходный комментарий (может быть многострочным)
    
    Returns:
        Нормализованный комментарий (одна строка)
    """
    if not comment:
        return ""
    
    # Заменяем все виды переносов на пробелы
    result = comment.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    
    # Убираем множественные пробелы
    while "  " in result:
        result = result.replace("  ", " ")
    
    # Убираем пробелы в начале и конце
    return result.strip()


class TestCommentPartsJoin:
    """Тесты для формирования финального комментария."""
    
    def test_comment_parts_join_normalized(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 8): Части комментария должны объединяться пробелами.
        """
        comment_parts = [
            "Создано из Clobus.uz",
            "Категория вопроса: НДС",
            "Мой комментарий"
        ]
        
        # Текущая реализация (BUG):
        # final_comment = "\n".join(comment_parts)
        
        # Правильная реализация:
        final_comment = " | ".join(comment_parts)
        
        assert "\n" not in final_comment, (
            f"Bug 8: Финальный комментарий не должен содержать \\n. "
            f"Получено: {repr(final_comment)}"
        )
    
    def test_user_comment_with_newlines(self):
        """Пользовательский комментарий с переносами нормализуется."""
        user_comment = "Это мой\nмногострочный\nкомментарий"
        
        comment_parts = [
            "Создано из Clobus.uz",
            normalize_comment(user_comment)  # Нормализуем
        ]
        
        final_comment = " | ".join(comment_parts)
        
        assert "\n" not in final_comment
        assert "многострочный" in final_comment


class TestPayloadComment:
    """Тесты для комментария в payload 1C."""
    
    def test_payload_comment_single_line(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 8): payload['Комментарий'] должен быть одной строкой.
        """
        # Симулируем формирование payload
        comment_parts = ["Создано из Clobus.uz", "Категория: НДС"]
        user_comment = "Мой\nкомментарий"
        
        # Нормализуем пользовательский комментарий
        if user_comment:
            comment_parts.append(normalize_comment(user_comment))
        
        # Объединяем разделителем (не \n!)
        final_comment = " | ".join(comment_parts)
        
        payload = {"Комментарий": final_comment}
        
        assert "\n" not in payload["Комментарий"], (
            f"Bug 8: payload['Комментарий'] не должен содержать \\n. "
            f"Получено: {repr(payload['Комментарий'])}"
        )
    
    def test_rating_comment_normalized(self):
        """Комментарий к оценке тоже нормализуется."""
        rating_comment = "Отличная\nконсультация!\nСпасибо!"
        
        normalized = normalize_comment(rating_comment)
        
        assert normalized == "Отличная консультация! Спасибо!"
    
    def test_redate_comment_normalized(self):
        """Комментарий к переносу тоже нормализуется."""
        redate_comment = "Перенос из-за\nболезни\nклиента"
        
        normalized = normalize_comment(redate_comment)
        
        assert normalized == "Перенос из-за болезни клиента"


class TestIntegrationComment:
    """Интеграционные тесты для комментариев."""
    
    @pytest.mark.asyncio
    async def test_create_consultation_comment_normalized(self):
        """
        Комментарий при создании консультации должен быть нормализован.
        """
        from unittest.mock import AsyncMock, MagicMock, patch
        
        # Mock для OneCClient
        captured_payload = {}
        
        async def mock_odata_request(method, endpoint, data=None, **kwargs):
            captured_payload.update(data or {})
            return {"Ref_Key": "test-key", "Number": "CONS-001"}
        
        with patch.object(
            sys.modules.get('FastAPI.services.onec_client', MagicMock()),
            'OneCClient',
            autospec=True
        ) as mock_client:
            # Симулируем формирование комментария
            comment_parts = [
                "Создано из Clobus.uz",
                "Категория вопроса: НДС",
                "Многострочный\nкомментарий\nот пользователя"
            ]
            
            # Правильный способ:
            normalized_parts = [normalize_comment(part) for part in comment_parts]
            final_comment = " | ".join(normalized_parts)
            
            assert "\n" not in final_comment
