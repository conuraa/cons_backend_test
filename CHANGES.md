# Changes: Update phone number in active 1C consultations

When a client changes their phone number via `POST /api/clients`, the new number
is now propagated to the `АбонентКакСвязаться` field in all active 1C consultations.

## File 1: `FastAPI/services/onec_client.py`

### Change: Add `contact_hint` parameter to `update_consultation_odata()`

**In the method signature**, add `contact_hint` parameter:

```diff
     async def update_consultation_odata(
         self,
         ref_key: str,
         ...
         is_chatwoot_status: bool = False,
-        check_changes: bool = True
+        check_changes: bool = True,
+        contact_hint: Optional[str] = None,
     ) -> Dict[str, Any]:
```

**In the docstring Args**, add:

```diff
             check_changes: Если True, проверяет текущие значения в ЦЛ перед обновлением
+            contact_hint: АбонентКакСвязаться (строка вида "Телефон / ФИО / Способ")
```

**After the `consultations_its` block**, add contact_hint handling:

```diff
         if consultations_its is not None:
             # Для КонсультацииИТС всегда обновляем, так как сравнение сложное
             payload["КонсультацииИТС"] = consultations_its

+        if contact_hint is not None:
+            current_hint = current_data.get("АбонентКакСвязаться") if current_data else None
+            if not current_data or current_hint != contact_hint:
+                payload["АбонентКакСвязаться"] = contact_hint
+
         # Если нет изменений - возвращаем текущие данные без запроса
```

---

## File 2: `FastAPI/routers/clients.py`

### Change A: New function `_update_active_consultations_phone()`

Insert **before** `_get_parent_client()` (line ~662):

```python
async def _update_active_consultations_phone(
    db: "AsyncSession",
    client: "Client",
    owner_client: "Client",
) -> None:
    """
    Обновляет поле АбонентКакСвязаться во всех активных консультациях клиента в 1С.
    Ошибки логируются, но не блокируют основной flow.
    """
    from ..services.onec_client import OneCClient
    from ..routers.consultations import _build_contact_hint
    from ..models import Consultation

    try:
        from sqlalchemy import select, or_

        owner_id = owner_client.client_id

        # All client_ids belonging to this owner
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

        # Active consultations synced to 1C
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
            return

        logger.info(
            f"Updating contact_hint in {len(consultations)} active consultation(s) "
            f"for client {client.client_id} (owner {owner_id})"
        )

        onec = OneCClient()

        for cons in consultations:
            try:
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
```

### Change B: Call the helper from `create_or_update_client()`

```diff
         # Синхронизируем клиента с 1C:ЦЛ (не блокируем создание клиента при ошибке)
         await _sync_client_to_onec(db, client)

+        # Обновляем номер телефона в активных заявках 1С
+        await _update_active_consultations_phone(db, client, owner_client)
+
         # Коммитим изменения cl_ref_key если он был установлен при синхронизации с 1C
```
