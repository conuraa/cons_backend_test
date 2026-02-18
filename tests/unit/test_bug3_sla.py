"""
Bug 3: Автоматические уведомления сбрасывают SLA First Response Time.

ПРОБЛЕМА:
    При создании консультации система отправляет автоматическое сообщение
    (информация о позиции в очереди) через send_message() с:
    - message_type="outgoing"
    - private=False
    
    Chatwoot считает это сообщение как "первый ответ агента" и сбрасывает
    SLA First Response Time таймер. Но это неправильно - это автоматическое
    системное уведомление, а не реальный ответ менеджера.

ОЖИДАЕМОЕ ПОВЕДЕНИЕ:
    Автоматические системные уведомления НЕ должны влиять на SLA метрики.
    Это достигается отправкой с параметром private=True.

РЕШЕНИЕ:
    1. Добавить параметр affects_sla=True в send_message()
    2. Если affects_sla=False, устанавливать private=True
    3. В send_queue_update_notification использовать affects_sla=False
    4. В send_manager_reassignment_notification использовать affects_sla=False

ТЕСТЫ:
    - Проверка что автоматические уведомления отправляются с private=True
    - Проверка что обычные сообщения отправляются с private=False
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

sys.path.insert(0, "/home/sada/cons_backend")


class TestBug3SlaNotifications:
    """Тесты для Bug 3: Автоматические уведомления и SLA."""
    
    @pytest.mark.asyncio
    async def test_queue_notification_uses_private_true(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 3): Уведомление о позиции в очереди должно быть private.
        
        Когда send_queue_update_notification отправляет сообщение,
        оно должно использовать private=True чтобы не сбрасывать SLA FRT.
        
        ЭТОТ ТЕСТ ДОЛЖЕН ПАДАТЬ ДО ИСПРАВЛЕНИЯ БАГА.
        """
        # Захватываем параметры вызова send_message
        captured_params = {}
        
        async def mock_send_message(conversation_id, content, message_type="outgoing", private=False):
            captured_params["conversation_id"] = conversation_id
            captured_params["content"] = content
            captured_params["message_type"] = message_type
            captured_params["private"] = private
            return {"id": 1}
        
        # Мокаем ChatwootClient
        mock_chatwoot = MagicMock()
        mock_chatwoot.send_message = AsyncMock(side_effect=mock_send_message)
        
        # Мокаем ManagerSelector.calculate_wait_time
        async def mock_calculate_wait_time(manager_key):
            return {
                "queue_position": 3,
                "estimated_wait_minutes": 45,
                "estimated_wait_hours": 0,
                "show_range": False,
            }
        
        mock_manager_selector = MagicMock()
        mock_manager_selector.calculate_wait_time = AsyncMock(side_effect=mock_calculate_wait_time)
        
        # Мокаем check_and_log_notification
        async def mock_check_notification(*args, **kwargs):
            return False  # Уведомление ещё не отправлялось
        
        # Мок консультации
        mock_consultation = MagicMock()
        mock_consultation.cons_id = "12345"
        mock_consultation.manager = "manager-key-123"
        mock_consultation.consultation_type = "Консультация по ведению учёта"
        
        # Мок БД сессии
        mock_db = AsyncMock()
        
        with patch("FastAPI.services.manager_notifications.ChatwootClient", return_value=mock_chatwoot):
            with patch("FastAPI.services.manager_notifications.ManagerSelector", return_value=mock_manager_selector):
                with patch("FastAPI.services.manager_notifications.check_and_log_notification", mock_check_notification):
                    from FastAPI.services.manager_notifications import send_queue_update_notification
                    
                    await send_queue_update_notification(
                        db=mock_db,
                        consultation=mock_consultation,
                        manager_key="manager-key-123"
                    )
        
        # Проверяем, что send_message был вызван
        assert "private" in captured_params, "send_message should have been called with private parameter"
        
        # BUG 3: private должен быть True для автоматических уведомлений
        # чтобы не сбрасывать SLA First Response Time
        assert captured_params["private"] is True, (
            f"Bug 3: Автоматическое уведомление о позиции в очереди должно быть private=True, "
            f"чтобы не сбрасывать SLA FRT. Текущее значение: private={captured_params['private']}"
        )
    
    @pytest.mark.asyncio
    async def test_reassignment_notification_uses_private_true(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 3): Уведомление о переназначении должно быть private.
        
        ЭТОТ ТЕСТ ДОЛЖЕН ПАДАТЬ ДО ИСПРАВЛЕНИЯ БАГА.
        """
        captured_params = {}
        
        async def mock_send_message(conversation_id, content, message_type="outgoing", private=False):
            captured_params["private"] = private
            return {"id": 1}
        
        mock_chatwoot = MagicMock()
        mock_chatwoot.send_message = AsyncMock(side_effect=mock_send_message)
        mock_chatwoot.assign_conversation_agent = AsyncMock(return_value={})
        
        mock_consultation = MagicMock()
        mock_consultation.cons_id = "12345"
        mock_consultation.manager = "new-manager-key"
        
        mock_db = AsyncMock()
        # Мок для поиска менеджера
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        async def mock_check_notification(*args, **kwargs):
            return False
        
        with patch("FastAPI.services.manager_notifications.ChatwootClient", return_value=mock_chatwoot):
            with patch("FastAPI.services.manager_notifications.check_and_log_notification", mock_check_notification):
                from FastAPI.services.manager_notifications import send_manager_reassignment_notification
                
                await send_manager_reassignment_notification(
                    db=mock_db,
                    consultation=mock_consultation,
                    old_manager_key="old-manager-key",
                    new_manager_key="new-manager-key",
                    reason="Test reason"
                )
        
        assert "private" in captured_params, "send_message should have been called"
        
        # BUG 3: private должен быть True
        assert captured_params["private"] is True, (
            f"Bug 3: Уведомление о переназначении должно быть private=True. "
            f"Текущее значение: private={captured_params['private']}"
        )


class TestSendMessagePrivateParameter:
    """Тесты для параметра private в send_message."""
    
    @pytest.mark.asyncio
    async def test_send_message_default_private_false(self):
        """По умолчанию private=False (для обычных сообщений)."""
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        
        captured_payload = {}
        
        async def mock_request(method, endpoint, data=None, params=None):
            captured_payload.update(data or {})
            return {"id": 1}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            
            async def mock_request_method(*args, **kwargs):
                captured_payload.update(kwargs.get("json", {}))
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = '{"id": 1}'
                mock_response.content = b'{"id": 1}'
                mock_response.json.return_value = {"id": 1}
                mock_response.raise_for_status = MagicMock()
                mock_response.reason_phrase = "OK"
                return mock_response
            
            mock_instance.request = AsyncMock(side_effect=mock_request_method)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            from FastAPI.services.chatwoot_client import ChatwootClient
            
            client = ChatwootClient()
            await client.send_message(
                conversation_id="12345",
                content="Test message"
            )
        
        assert captured_payload.get("private") is False, (
            f"По умолчанию private должен быть False, got: {captured_payload.get('private')}"
        )
    
    @pytest.mark.asyncio
    async def test_send_message_explicit_private_true(self):
        """Можно явно указать private=True."""
        import sys
        sys.path.insert(0, "/home/sada/cons_backend")
        
        captured_payload = {}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            
            async def mock_request_method(*args, **kwargs):
                captured_payload.update(kwargs.get("json", {}))
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = '{"id": 1}'
                mock_response.content = b'{"id": 1}'
                mock_response.json.return_value = {"id": 1}
                mock_response.raise_for_status = MagicMock()
                mock_response.reason_phrase = "OK"
                return mock_response
            
            mock_instance.request = AsyncMock(side_effect=mock_request_method)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            from FastAPI.services.chatwoot_client import ChatwootClient
            
            client = ChatwootClient()
            await client.send_message(
                conversation_id="12345",
                content="Private note",
                private=True  # Явно указываем private
            )
        
        assert captured_payload.get("private") is True, (
            f"private=True должен передаваться в payload, got: {captured_payload.get('private')}"
        )
