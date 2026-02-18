"""Роутер для toast-уведомлений (chat token для WebSocket)."""
import logging
import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..dependencies.security import verify_front_secret
from ..models import Client, Consultation
from ..schemas.notifications import ChatTokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_front_secret)])


def _build_ws_url(base_url: str) -> str | None:
    """Собрать WebSocket URL из базового URL Chatwoot."""
    if not base_url:
        return None
    url = re.sub(r"^https:", "wss:", base_url, flags=re.IGNORECASE)
    url = re.sub(r"^http:", "ws:", url, flags=re.IGNORECASE)
    return url.rstrip("/") + "/cable"


def _build_chat_url(cons_id: str) -> str | None:
    """Собрать динамическую ссылку на страницу чата консультации."""
    base = settings.SITE_BASE_URL or settings.TELEGRAM_WEBAPP_URL
    if not base:
        return None
    return f"{base.rstrip('/')}/subscriptions?openChat={cons_id}"


@router.get("/chat-token", response_model=ChatTokenResponse)
async def get_chat_token(
    subscriber_id: str = Query(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[\w\-]+$",
        description="code_abonent подписчика",
    ),
    db: AsyncSession = Depends(get_db),
) -> ChatTokenResponse:
    """
    Возвращает pubsub_token клиента для WebSocket-подключения к Chatwoot.

    Используется header-скриптом на сайте для получения toast-уведомлений
    о новых сообщениях оператора на любой странице.

    Ответ включает:
    - **pubsub_token** — токен для ActionCable WebSocket Chatwoot
    - **ws_url** — готовый WebSocket URL (wss://…/cable)
    - **chat_url** — динамическая ссылка на страницу чата (для клика по toast)
    - **consultation_id** — ID активной консультации
    """
    empty = ChatTokenResponse()

    # Найти всех клиентов по code_abonent (может быть несколько записей)
    result = await db.execute(
        select(Client)
        .where(Client.code_abonent == subscriber_id)
        .order_by(Client.updated_at.desc())
    )
    clients = result.scalars().all()
    if not clients:
        return empty

    # Собрать client_id всех записей
    client_ids = [c.client_id for c in clients]

    # Найти последнюю активную консультацию среди всех клиентов
    inactive_statuses = ("closed", "resolved", "cancelled")
    result = await db.execute(
        select(Consultation.cons_id, Consultation.client_id)
        .where(
            Consultation.client_id.in_(client_ids),
            Consultation.status.notin_(inactive_statuses),
        )
        .order_by(Consultation.create_date.desc())
        .limit(1)
    )
    row = result.first()

    if not row:
        return empty

    active_cons_id, active_client_id = row

    # Найти pubsub_token у клиента-владельца консультации,
    # а если нет — у любого клиента с этим code_abonent
    token = None
    clients_by_id = {c.client_id: c for c in clients}
    owner = clients_by_id.get(active_client_id)
    if owner and owner.chatwoot_pubsub_token:
        token = owner.chatwoot_pubsub_token
    else:
        for c in clients:
            if c.chatwoot_pubsub_token:
                token = c.chatwoot_pubsub_token
                break

    if isinstance(token, (bytes, memoryview)):
        token = bytes(token).decode("utf-8")

    if not token:
        return empty

    chatwoot_base = settings.CHATWOOT_API_URL or None
    cons_id_str = str(active_cons_id)

    return ChatTokenResponse(
        pubsub_token=token,
        chatwoot_base_url=chatwoot_base,
        ws_url=_build_ws_url(chatwoot_base),
        has_active_consultation=True,
        consultation_id=cons_id_str,
        chat_url=_build_chat_url(cons_id_str),
    )
