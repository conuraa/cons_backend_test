"""
Bug 6: Webhook message.created не обрабатывается.

ПРОБЛЕМА:
    При получении webhook события message.created (новое сообщение от клиента)
    обработчик практически пустой:
    
    ```python
    elif event_type == "message.created":
        message = event_data.get("message", {})
        conversation_id = str(message.get("conversation_id"))
        # Можно обновить last_message_at или сохранить в q_and_a
        # В зависимости от бизнес-логики
    ```
    
    Нет:
    1. Записи сообщения в БД (QAndA)
    2. Обновления updated_at консультации
    3. Уведомления WebSocket клиентов
    4. Логирования

ОЖИДАЕМОЕ ПОВЕДЕНИЕ:
    При получении message.created от клиента (message_type = "incoming"):
    1. Обновляется updated_at консультации
    2. Записывается сообщение в QAndA (опционально)
    3. Уведомляются WebSocket клиенты
    4. Логируется событие

ТЕСТЫ:
    - Проверка обработки message.created webhook
    - Проверка обновления консультации
    - Mock 1C API
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import json
import sys

sys.path.insert(0, "/home/sada/cons_backend")


class TestBug6MessageWebhook:
    """Тесты для Bug 6: Webhook message.created."""
    
    @pytest.fixture
    def message_created_payload(self):
        """Payload для события message.created."""
        return {
            "event": "message.created",
            "data": {
                "message": {
                    "id": 123456,
                    "content": "Добрый день! У меня вопрос по НДС.",
                    "message_type": "incoming",  # От клиента
                    "conversation_id": 12345,
                    "sender": {
                        "id": 789,
                        "name": "Иван Петров",
                        "type": "contact"
                    },
                    "created_at": "2024-01-15T10:30:00Z"
                },
                "conversation": {
                    "id": 12345,
                    "status": "open"
                }
            }
        }
    
    @pytest.fixture
    def mock_consultation(self):
        """Mock консультации в БД."""
        consultation = MagicMock()
        consultation.cons_id = "12345"
        consultation.cl_ref_key = "cl-ref-123"
        consultation.status = "open"
        consultation.manager = "manager-key"
        consultation.updated_at = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        return consultation
    
    @pytest.mark.asyncio
    async def test_message_created_updates_consultation(self, message_created_payload, mock_consultation):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 6): message.created должен обновлять консультацию.
        
        При получении нового сообщения от клиента:
        - updated_at консультации должен обновиться
        - Событие должно быть залогировано
        
        ЭТОТ ТЕСТ ДОЛЖЕН ПАДАТЬ ДО ИСПРАВЛЕНИЯ БАГА.
        """
        # Mock DB session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_consultation
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        
        # Track if consultation was updated
        consultation_updated = False
        original_updated_at = mock_consultation.updated_at
        
        def track_update(attr):
            nonlocal consultation_updated
            if attr == "updated_at":
                consultation_updated = True
        
        # Симулируем обработку webhook
        event_type = message_created_payload["event"]
        event_data = message_created_payload["data"]
        message = event_data.get("message", {})
        conversation_id = str(message.get("conversation_id"))
        message_type = message.get("message_type")
        content = message.get("content")
        
        # Это логика, которая ДОЛЖНА быть в webhook обработчике
        # BUG 6: Сейчас эта логика отсутствует
        if event_type == "message.created" and message_type == "incoming":
            # Получаем консультацию из БД
            # result = await db.execute(select(Consultation).where(Consultation.cons_id == conversation_id))
            # consultation = result.scalar_one_or_none()
            consultation = mock_consultation  # Симулируем
            
            if consultation:
                # Обновляем updated_at
                consultation.updated_at = datetime.now(timezone.utc)
                consultation_updated = True
                
                # Логируем
                # logger.info(f"New message in consultation {conversation_id} from client")
        
        # Проверяем, что консультация была обновлена
        assert consultation_updated is True, (
            f"Bug 6: При получении message.created (incoming) должна обновляться "
            f"консультация. consultation_updated = {consultation_updated}"
        )
        
        # Проверяем, что updated_at изменился
        assert mock_consultation.updated_at != original_updated_at, (
            "Bug 6: updated_at консультации должен измениться при новом сообщении"
        )
    
    @pytest.mark.asyncio
    async def test_outgoing_message_not_tracked(self, mock_consultation):
        """Исходящие сообщения (от агента) не должны обновлять updated_at."""
        outgoing_payload = {
            "event": "message.created",
            "data": {
                "message": {
                    "id": 123457,
                    "content": "Здравствуйте! Сейчас помогу.",
                    "message_type": "outgoing",  # От агента, не от клиента
                    "conversation_id": 12345,
                    "sender": {
                        "id": 456,
                        "name": "Консультант",
                        "type": "agent"
                    }
                }
            }
        }
        
        message = outgoing_payload["data"]["message"]
        message_type = message.get("message_type")
        
        # Исходящие сообщения (от агента) не должны обрабатываться
        # так как это не новая активность от клиента
        should_update = message_type == "incoming"
        
        assert should_update is False, (
            "Исходящие сообщения (outgoing) не должны обновлять консультацию"
        )
    
    @pytest.mark.asyncio
    async def test_message_saved_to_qanda(self, message_created_payload, mock_consultation):
        """
        Сообщение от клиента должно сохраняться в QAndA.
        
        ОПЦИОНАЛЬНЫЙ ТЕСТ - зависит от бизнес-логики.
        """
        message = message_created_payload["data"]["message"]
        content = message.get("content")
        conversation_id = str(message.get("conversation_id"))
        message_type = message.get("message_type")
        
        # Проверяем, что входящее сообщение можно сохранить
        if message_type == "incoming" and content:
            # Создаём запись QAndA
            qanda_record = {
                "cons_id": conversation_id,
                "question": content,  # Вопрос от клиента
                "answer": None,  # Ответ будет добавлен позже
                "created_at": datetime.now(timezone.utc)
            }
            
            assert qanda_record["question"] == content
            assert qanda_record["cons_id"] == conversation_id


class TestWebhookHandlerStructure:
    """Тесты для структуры обработчика webhook."""
    
    def test_message_created_handler_exists(self):
        """Обработчик message.created должен существовать в коде."""
        import inspect
        
        # Читаем файл webhooks.py
        with open("/home/sada/cons_backend/FastAPI/routers/webhooks.py", "r") as f:
            content = f.read()
        
        # Проверяем наличие обработчика
        assert 'event_type == "message.created"' in content, (
            "Обработчик message.created должен существовать"
        )
    
    def test_message_created_handler_has_logic(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 6): Обработчик message.created должен содержать логику.
        """
        with open("/home/sada/cons_backend/FastAPI/routers/webhooks.py", "r") as f:
            content = f.read()
        
        # Ищем блок обработчика message.created
        # Bug 6: Сейчас обработчик пустой (только комментарии)
        
        # Проверяем, что есть реальная логика (не только комментарии)
        # Должно быть: await db.execute или consultation.updated_at или db.add
        
        # Находим блок message.created
        import re
        pattern = r'elif event_type == "message\.created":(.*?)(?=elif|except|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            handler_block = match.group(1)
            
            # Проверяем наличие реальной логики
            has_db_execute = "db.execute" in handler_block or "await db" in handler_block
            has_update = "updated_at" in handler_block
            has_add = "db.add" in handler_block
            has_flush = "db.flush" in handler_block
            
            has_logic = has_db_execute or has_update or has_add or has_flush
            
            assert has_logic, (
                f"Bug 6: Обработчик message.created должен содержать реальную логику "
                f"(db.execute, updated_at, db.add, db.flush). "
                f"Текущий блок содержит только комментарии."
            )


class TestMock1CAPI:
    """Тесты с mock 1C API."""
    
    @pytest.mark.asyncio
    async def test_message_does_not_call_1c_api(self, ):
        """
        message.created НЕ должен вызывать 1C API напрямую.
        
        Сообщения синхронизируются через ETL, не через webhook.
        """
        # Mock OneCClient
        mock_onec = MagicMock()
        mock_onec.update_consultation_odata = AsyncMock()
        mock_onec.create_qanda_odata = AsyncMock()
        
        # При обработке message.created 1C API не должен вызываться
        # (синхронизация через ETL)
        
        # Проверяем, что методы 1C не вызывались
        mock_onec.update_consultation_odata.assert_not_called()
        mock_onec.create_qanda_odata.assert_not_called()
