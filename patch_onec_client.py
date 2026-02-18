"""
Patch for /home/sada/cons_backend/FastAPI/services/onec_client.py

Adds `contact_hint` parameter to `update_consultation_odata()` method.

Apply manually or run this script on the server:
    python3 patch_onec_client.py
"""
import re

FILE_PATH = "/home/sada/cons_backend/FastAPI/services/onec_client.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add contact_hint parameter to the signature
old_sig = """\
        check_changes: bool = True
    ) -> Dict[str, Any]:"""

new_sig = """\
        check_changes: bool = True,
        contact_hint: Optional[str] = None,
    ) -> Dict[str, Any]:"""

assert old_sig in content, "Could not find update_consultation_odata signature to patch"
content = content.replace(old_sig, new_sig, 1)

# 2. Add contact_hint to docstring Args section
old_doc = """\
            check_changes: Если True, проверяет текущие значения в ЦЛ перед обновлением"""

new_doc = """\
            check_changes: Если True, проверяет текущие значения в ЦЛ перед обновлением
            contact_hint: АбонентКакСвязаться (строка вида "Телефон / ФИО / Способ")"""

assert old_doc in content, "Could not find docstring to patch"
content = content.replace(old_doc, new_doc, 1)

# 3. Add contact_hint handling in the payload building section (after consultations_its block)
old_its_block = """\
        if consultations_its is not None:
            # Для КонсультацииИТС всегда обновляем, так как сравнение сложное
            payload["КонсультацииИТС"] = consultations_its"""

new_its_block = """\
        if consultations_its is not None:
            # Для КонсультацииИТС всегда обновляем, так как сравнение сложное
            payload["КонсультацииИТС"] = consultations_its

        if contact_hint is not None:
            current_hint = current_data.get("АбонентКакСвязаться") if current_data else None
            if not current_data or current_hint != contact_hint:
                payload["АбонентКакСвязаться"] = contact_hint"""

assert old_its_block in content, "Could not find consultations_its block to patch"
content = content.replace(old_its_block, new_its_block, 1)

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✓ Patched {FILE_PATH} successfully")
print("  - Added contact_hint parameter to update_consultation_odata()")
print("  - Added contact_hint to docstring")
print("  - Added contact_hint payload handling")
