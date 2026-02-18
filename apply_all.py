"""Apply both patches: onec_client.py and clients.py"""
import sys

# =============================================
# PATCH 1: services/onec_client.py
# =============================================
FILE1 = "/app/FastAPI/services/onec_client.py"

with open(FILE1, "r", encoding="utf-8") as f:
    content1 = f.read()

# 1a. Add contact_hint to update_consultation_odata signature
old_sig = "        check_changes: bool = True\n    ) -> Dict[str, Any]:"
# Only patch if not already patched
if "contact_hint: Optional[str] = None,\n    ) -> Dict[str, Any]:" not in content1:
    new_sig = "        check_changes: bool = True,\n        contact_hint: Optional[str] = None,\n    ) -> Dict[str, Any]:"
    # There might be two occurrences - we need the one in update_consultation_odata (around line 487)
    # The create method already has contact_hint, so find the right one
    idx = content1.find(old_sig)
    if idx < 0:
        print(f"ERROR: Could not find signature anchor in {FILE1}")
        sys.exit(1)
    content1 = content1[:idx] + new_sig + content1[idx + len(old_sig):]
    print("  - Added contact_hint to update_consultation_odata() signature")
else:
    print("  - Signature already patched, skipping")

# 1b. Add contact_hint to docstring
old_doc = "            check_changes: Если True, проверяет текущие значения в ЦЛ перед обновлением"
new_doc = old_doc + '\n            contact_hint: АбонентКакСвязаться (строка вида "Телефон / ФИО / Способ")'
if 'contact_hint: АбонентКакСвязаться' not in content1.split("update_consultation_odata")[-1].split("def ")[0]:
    if old_doc in content1:
        content1 = content1.replace(old_doc, new_doc, 1)
        print("  - Added contact_hint to docstring")
    else:
        print("  WARNING: Could not find docstring anchor")
else:
    print("  - Docstring already patched, skipping")

# 1c. Add contact_hint handling in payload section
old_its = '        if consultations_its is not None:\n            # Для КонсультацииИТС всегда обновляем, так как сравнение сложное\n            payload["КонсультацииИТС"] = consultations_its'
new_its = old_its + """

        if contact_hint is not None:
            current_hint = current_data.get("АбонентКакСвязаться") if current_data else None
            if not current_data or current_hint != contact_hint:
                payload["АбонентКакСвязаться"] = contact_hint"""

if "АбонентКакСвязаться" not in content1.split("update_consultation_odata")[-1].split("def ")[0]:
    if old_its in content1:
        content1 = content1.replace(old_its, new_its, 1)
        print("  - Added contact_hint payload handling")
    else:
        print("  WARNING: Could not find consultations_its block")
else:
    print("  - Payload handling already patched, skipping")

with open(FILE1, "w", encoding="utf-8") as f:
    f.write(content1)
print(f"OK Patched {FILE1}")

# =============================================
# PATCH 2: routers/clients.py
# =============================================
FILE2 = "/app/FastAPI/routers/clients.py"

with open(FILE2, "r", encoding="utf-8") as f:
    content2 = f.read()

# 2a. Insert _update_active_consultations_phone() before _get_parent_client()
NEW_FUNC = '''async def _update_active_consultations_phone(
    db,
    client,
    owner_client,
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
        from sqlalchemy import select, or_

        owner_id = owner_client.client_id

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


'''

anchor = "async def _get_parent_client("
if "_update_active_consultations_phone" not in content2:
    if anchor in content2:
        content2 = content2.replace(anchor, NEW_FUNC + anchor, 1)
        print("  - Added _update_active_consultations_phone() function")
    else:
        print(f"  ERROR: Could not find anchor: {anchor}")
        sys.exit(1)
else:
    print("  - Function already exists, skipping")

# 2b. Call helper from create_or_update_client()
call_anchor = "await _sync_client_to_onec(db, client)"
new_call = """await _sync_client_to_onec(db, client)

        # Обновляем номер телефона в активных заявках 1С
        await _update_active_consultations_phone(db, client, owner_client)"""

if "_update_active_consultations_phone(db, client, owner_client)" not in content2:
    idx = content2.find(call_anchor)
    if idx < 0:
        print(f"  ERROR: Could not find call anchor: {call_anchor}")
        sys.exit(1)
    content2 = content2[:idx] + new_call + content2[idx + len(call_anchor):]
    print("  - Added call to _update_active_consultations_phone()")
else:
    print("  - Call already exists, skipping")

with open(FILE2, "w", encoding="utf-8") as f:
    f.write(content2)
print(f"OK Patched {FILE2}")

print("\nAll patches applied successfully!")
