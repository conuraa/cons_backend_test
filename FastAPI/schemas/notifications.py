"""Схемы для уведомлений"""
from pydantic import BaseModel
from typing import Optional


class ChatTokenResponse(BaseModel):
    """Ответ с pubsub_token для WebSocket-подключения к Chatwoot"""
    pubsub_token: Optional[str] = None
    chatwoot_base_url: Optional[str] = None
    ws_url: Optional[str] = None
    has_active_consultation: bool = False
    consultation_id: Optional[str] = None
    chat_url: Optional[str] = None
