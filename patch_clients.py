"""
Patch for /home/sada/cons_backend/FastAPI/routers/clients.py

Adds:
1. `_update_active_consultations_phone()` helper function
2. Call to the helper from `create_or_update_client()`

Apply manually or run this script on the server:
    python3 patch_clients.py
"""

FILE_PATH = "/home/sada/cons_backend/FastAPI/routers/clients.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# ===========================================================================
# 1. Add _update_active_consultations_phone() helper AFTER _sync_client_to_onec()
# ===========================================================================

# Find the end of _sync_client_to_onec() — it ends with the except block's logger.error line
# The next function is _get_parent_client at line 662.
# We insert the new function between them.

old_anchor = '''\
async def _get_parent_client('''

new_helper_plus_anchor = '''\
async def _update_active_consultations_phone(
    db: "AsyncSession",
    client: "Client",
    owner_client: "Client",
) -> None:
    """
    Обновляет поле АбонентКакСвязаться во всех активных консультациях клиента в 1С.

    Вызывается при смене номера телефона клиента, чтобы менеджер видел актуальный номер.
    Ошибки логируются, но не блокируют основной flow.
    """
    from ..services.onec_client import OneCClient
    from ..routers.consultations import _build_contact_hint
    from ..models import Consultation

    try:
        # Собираем все client_id, которые принадлежат этому владельцу:
        # сам owner + все его дочерние клиенты
        from sqlalchemy import select, or_

        owner_id = owner_client.client_id

        # Находим все client_id, принадлежащие owner (parent_id == owner_id) или сам owner
        client_ids_result = await db.execute(
            select(Client.client_id).where(
                or_(
                    Client.client_id == owner_id,
                    Client.parent_id == owner_id,
                )
            )
        )
        client_ids = [row[0] for row in client_ids_result.all()]

        if not client_ids:
            return

        # Получаем все активные консультации с cl_ref_key для этих клиентов
        result = await db.execute(
            select(Consultation).where(
                Consultation.client_id.in_(client_ids),
                Consultation.cl_ref_key.isnot(None),
                Consultation.cl_ref_key != "",
                or_(
                    Consultation.status.is_(None),
                    Consultation.status.notin_(["cancelled", "closed"]),
                ),
            )
        )
        consultations = result.scalars().all()

        if not consultations:
            logger.debug(f"No active consultations to update phone for client {client.client_id}")
            return

        logger.info(
            f"Updating contact_hint in {len(consultations)} active consultation(s) "
            f"for client {client.client_id} (owner {owner_id})"
        )

        onec = OneCClient()

        for cons in consultations:
            try:
                # Получаем клиента этой консультации для построения contact_hint
                cons_client_result = await db.execute(
                    select(Client).where(Client.client_id == cons.client_id)
                )
                cons_client = cons_client_result.scalar_one_or_none()
                if not cons_client:
                    continue

                contact_hint = _build_contact_hint(
                    client=cons_client,
                    owner=owner_client,
                    source=cons.source,
                )
                if contact_hint:
                    await onec.update_consultation_odata(
                        ref_key=cons.cl_ref_key,
                        contact_hint=contact_hint,
                    )
                    logger.info(
                        f"Updated contact_hint for consultation {cons.cons_id} "
                        f"(cl_ref_key={cons.cl_ref_key[:20]}): {contact_hint}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to update contact_hint for consultation {cons.cons_id}: {e}",
                    exc_info=True,
                )
    except Exception as e:
        logger.error(
            f"Failed to update active consultations phone for client {client.client_id}: {e}",
            exc_info=True,
        )


async def _get_parent_client('''

assert old_anchor in content, f"Could not find _get_parent_client function definition"
content = content.replace(old_anchor, new_helper_plus_anchor, 1)

# ===========================================================================
# 2. Call _update_active_consultations_phone() from create_or_update_client()
# ===========================================================================

# Insert after _sync_client_to_onec(db, client) call
old_sync_call = """\
        # Синхронизируем клиента с 1C:ЦЛ (не блокируем создание клиента при ошибке)
        await _sync_client_to_onec(db, client)

        # Коммитим изменения cl_ref_key если он был установлен при синхронизации с 1C"""

new_sync_call = """\
        # Синхронизируем клиента с 1C:ЦЛ (не блокируем создание клиента при ошибке)
        await _sync_client_to_onec(db, client)

        # Обновляем номер телефона в активных заявках 1С
        await _update_active_consultations_phone(db, client, owner_client)

        # Коммитим изменения cl_ref_key если он был установлен при синхронизации с 1C"""

assert old_sync_call in content, "Could not find _sync_client_to_onec call site in create_or_update_client"
content = content.replace(old_sync_call, new_sync_call, 1)

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✓ Patched {FILE_PATH} successfully")
print("  - Added _update_active_consultations_phone() helper function")
print("  - Added call from create_or_update_client() after _sync_client_to_onec()")
