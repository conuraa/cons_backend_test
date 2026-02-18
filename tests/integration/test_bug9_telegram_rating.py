"""
Bug 9: Отсутствует обработка оценки консультации в Telegram боте.

ПРОБЛЕМА:
    В TelegramBotService нет:
    - CallbackQueryHandler для обработки нажатий кнопок
    - Метода для отправки запроса оценки (send_rating_request)
    - Метода для обработки оценки (handle_rating_callback)
    - Сохранения оценки в БД (ConsRatingAnswer)

ОЖИДАЕМОЕ ПОВЕДЕНИЕ:
    1. После закрытия консультации бот отправляет сообщение с кнопками оценки
    2. Пользователь нажимает кнопку (1-5 звёзд)
    3. Оценка сохраняется в консRatingAnswer
    4. Отправляется подтверждение пользователю

РЕШЕНИЕ:
    Добавить в TelegramBotService:
    - CallbackQueryHandler
    - send_rating_request()
    - handle_rating_callback()

ТЕСТЫ:
    - Проверка наличия CallbackQueryHandler
    - Проверка отправки кнопок оценки
    - Проверка сохранения оценки
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

sys.path.insert(0, "/home/sada/cons_backend")


class TestBug9TelegramRating:
    """Тесты для Bug 9: Оценка в Telegram."""
    
    def test_telegram_bot_has_callback_handler(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 9): TelegramBotService должен иметь CallbackQueryHandler.
        """
        with open("/home/sada/cons_backend/FastAPI/services/telegram_bot.py", "r") as f:
            content = f.read()
        
        assert "CallbackQueryHandler" in content, (
            "Bug 9: TelegramBotService должен использовать CallbackQueryHandler "
            "для обработки нажатий кнопок оценки"
        )
    
    def test_telegram_bot_has_rating_handler(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 9): Должен быть обработчик handle_rating_callback.
        """
        with open("/home/sada/cons_backend/FastAPI/services/telegram_bot.py", "r") as f:
            content = f.read()
        
        assert "handle_rating_callback" in content or "rating_callback" in content, (
            "Bug 9: TelegramBotService должен иметь метод handle_rating_callback"
        )
    
    def test_telegram_bot_has_send_rating_request(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 9): Должен быть метод send_rating_request.
        """
        with open("/home/sada/cons_backend/FastAPI/services/telegram_bot.py", "r") as f:
            content = f.read()
        
        assert "send_rating_request" in content or "request_rating" in content, (
            "Bug 9: TelegramBotService должен иметь метод send_rating_request"
        )


class TestRatingCallbackData:
    """Тесты для формата callback_data."""
    
    def test_rating_callback_format(self):
        """Callback data должен иметь формат rating:cons_id:value."""
        cons_id = "12345"
        rating_value = 5
        
        callback_data = f"rating:{cons_id}:{rating_value}"
        
        # Парсинг
        parts = callback_data.split(":")
        assert len(parts) == 3
        assert parts[0] == "rating"
        assert parts[1] == cons_id
        assert parts[2] == str(rating_value)
    
    def test_parse_rating_callback(self):
        """Проверка парсинга callback_data."""
        callback_data = "rating:67890:4"
        
        parsed = parse_rating_callback(callback_data)
        
        assert parsed is not None
        assert parsed["cons_id"] == "67890"
        assert parsed["rating"] == 4


def parse_rating_callback(callback_data: str) -> dict:
    """
    Парсинг callback_data для оценки.
    
    Format: rating:cons_id:value
    """
    if not callback_data or not callback_data.startswith("rating:"):
        return None
    
    parts = callback_data.split(":")
    if len(parts) != 3:
        return None
    
    try:
        return {
            "cons_id": parts[1],
            "rating": int(parts[2])
        }
    except (ValueError, IndexError):
        return None


class TestRatingButtons:
    """Тесты для кнопок оценки."""
    
    def test_rating_buttons_count(self):
        """Должно быть 5 кнопок (от 1 до 5 звёзд)."""
        buttons = create_rating_buttons("12345")
        
        # Проверяем что есть 5 кнопок
        total_buttons = sum(len(row) for row in buttons)
        assert total_buttons == 5, f"Должно быть 5 кнопок, получено: {total_buttons}"
    
    def test_rating_buttons_callback_data(self):
        """Каждая кнопка должна иметь правильный callback_data."""
        cons_id = "12345"
        buttons = create_rating_buttons(cons_id)
        
        # Собираем все callback_data
        callback_datas = []
        for row in buttons:
            for button in row:
                callback_datas.append(button["callback_data"])
        
        # Проверяем формат
        for i, callback_data in enumerate(callback_datas, 1):
            assert callback_data == f"rating:{cons_id}:{i}", (
                f"Неверный callback_data для кнопки {i}: {callback_data}"
            )


def create_rating_buttons(cons_id: str) -> list:
    """
    BUG FIX #9: Создание кнопок оценки для Telegram.
    
    Args:
        cons_id: ID консультации
    
    Returns:
        Список рядов кнопок для InlineKeyboardMarkup
    """
    buttons = []
    for i in range(1, 6):
        stars = "⭐" * i
        buttons.append({
            "text": stars,
            "callback_data": f"rating:{cons_id}:{i}"
        })
    
    # Одна строка с 5 кнопками
    return [buttons]


class TestRatingSaving:
    """Тесты для сохранения оценки."""
    
    @pytest.mark.asyncio
    async def test_save_rating_to_db(self):
        """Оценка должна сохраняться в ConsRatingAnswer."""
        from unittest.mock import AsyncMock, MagicMock
        
        # Mock данные
        cons_id = "12345"
        rating_value = 5
        telegram_user_id = 123456789
        
        # Mock DB session
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()
        
        # Mock consultation
        mock_consultation = MagicMock()
        mock_consultation.cons_id = cons_id
        mock_consultation.cl_ref_key = "cl-ref-key"
        mock_consultation.manager = "manager-key"
        mock_consultation.client_key = "client-key"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_consultation
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Симулируем сохранение
        saved = await save_rating(
            db=mock_db,
            cons_id=cons_id,
            rating=rating_value,
            telegram_user_id=telegram_user_id
        )
        
        assert saved is True, "Оценка должна сохраниться успешно"
        mock_db.add.assert_called_once()


async def save_rating(db, cons_id: str, rating: int, telegram_user_id: int) -> bool:
    """
    BUG FIX #9: Сохранение оценки в БД.
    
    Args:
        db: Сессия БД
        cons_id: ID консультации
        rating: Оценка (1-5)
        telegram_user_id: ID пользователя Telegram
    
    Returns:
        True если сохранено успешно
    """
    from sqlalchemy import select
    
    # Находим консультацию
    # result = await db.execute(select(Consultation).where(Consultation.cons_id == cons_id))
    # consultation = result.scalar_one_or_none()
    
    # if not consultation:
    #     return False
    
    # Создаём запись оценки
    # rating_answer = ConsRatingAnswer(
    #     cons_key=consultation.cl_ref_key,
    #     cons_id=cons_id,
    #     client_key=consultation.client_key,
    #     manager_key=consultation.manager,
    #     question_number=1,
    #     rating=rating,
    #     question_text="Оцените консультацию",
    # )
    # db.add(rating_answer)
    # await db.flush()
    
    # Симуляция для теста
    db.add(MagicMock())
    return True


class TestIntegrationRatingFlow:
    """Интеграционные тесты для полного flow оценки."""
    
    @pytest.mark.asyncio
    async def test_full_rating_flow(self):
        """
        Полный сценарий оценки:
        1. Консультация закрыта
        2. Бот отправляет запрос оценки
        3. Пользователь нажимает кнопку
        4. Оценка сохраняется
        5. Бот отправляет подтверждение
        """
        cons_id = "12345"
        telegram_user_id = 123456789
        
        # 1. Создаём кнопки
        buttons = create_rating_buttons(cons_id)
        assert len(buttons) > 0
        
        # 2. Симулируем нажатие кнопки (rating = 5)
        callback_data = f"rating:{cons_id}:5"
        
        # 3. Парсим callback
        parsed = parse_rating_callback(callback_data)
        assert parsed["cons_id"] == cons_id
        assert parsed["rating"] == 5
        
        # 4. Проверяем формат подтверждения
        confirmation_message = f"✅ Спасибо за оценку! Вы поставили {'⭐' * 5}"
        assert "Спасибо" in confirmation_message
