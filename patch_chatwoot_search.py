"""
Patch for /app/FastAPI/services/chatwoot_client.py

Fixes find_contact_by_identifier/email/phone to use Chatwoot /contacts/search API
instead of broken /contacts?identifier=... which doesn't actually filter.
"""
import sys

FILE_PATH = "/app/FastAPI/services/chatwoot_client.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# ==========================================
# Fix find_contact_by_identifier
# ==========================================
old_find_by_identifier = '''    async def find_contact_by_identifier(
        self,
        identifier: str
    ) -> Optional[Dict[str, Any]]:
        """
        Поиск контакта по identifier.

        Args:
            identifier: Уникальный идентификатор контакта

        Returns:
            Dict с данными контакта или None
        """
        try:
            # Пытаемся получить список контактов и найти по identifier
            # Chatwoot API может поддерживать поиск через query параметр
            response = await self._request(
                "GET",
                f"/api/v1/accounts/{self.account_id}/contacts",
                params={"identifier": identifier}
            )
            # Ответ может содержать массив контактов или объект с payload
            if isinstance(response, dict):
                contacts = response.get("payload", [])
                if isinstance(contacts, list):
                    for contact in contacts:
                        if contact.get("identifier") == identifier:
                            return contact
                elif isinstance(contacts, dict) and contacts.get("identifier") == identifier:
                    return contacts
        except Exception as e:
            logger.debug(f"Failed to search contact by identifier {identifier}: {e}")
        return None'''

new_find_by_identifier = '''    async def find_contact_by_identifier(
        self,
        identifier: str
    ) -> Optional[Dict[str, Any]]:
        """
        Поиск контакта по identifier через /contacts/search API.

        Args:
            identifier: Уникальный идентификатор контакта

        Returns:
            Dict с данными контакта или None
        """
        try:
            response = await self._request(
                "GET",
                f"/api/v1/accounts/{self.account_id}/contacts/search",
                params={"q": identifier, "include_contacts": "true"}
            )
            if isinstance(response, dict):
                contacts = response.get("payload", [])
                if isinstance(contacts, list):
                    for contact in contacts:
                        if contact.get("identifier") == identifier:
                            return contact
        except Exception as e:
            logger.debug(f"Failed to search contact by identifier {identifier}: {e}")
        return None'''

assert old_find_by_identifier in content, "Could not find find_contact_by_identifier"
content = content.replace(old_find_by_identifier, new_find_by_identifier, 1)
print("  - Fixed find_contact_by_identifier")

# ==========================================
# Fix find_contact_by_email
# ==========================================
old_find_by_email = '''    async def find_contact_by_email(
        self,
        email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Поиск контакта по email.

        Args:
            email: Email контакта

        Returns:
            Dict с данными контакта или None
        """
        try:
            response = await self._request(
                "GET",
                f"/api/v1/accounts/{self.account_id}/contacts",
                params={"email": email}
            )
            if isinstance(response, dict):
                contacts = response.get("payload", [])
                if isinstance(contacts, list):
                    for contact in contacts:
                        if contact.get("email") == email:
                            return contact
                elif isinstance(contacts, dict) and contacts.get("email") == email:
                    return contacts
        except Exception as e:
            logger.debug(f"Failed to search contact by email {email}: {e}")
        return None'''

new_find_by_email = '''    async def find_contact_by_email(
        self,
        email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Поиск контакта по email через /contacts/search API.

        Args:
            email: Email контакта

        Returns:
            Dict с данными контакта или None
        """
        try:
            response = await self._request(
                "GET",
                f"/api/v1/accounts/{self.account_id}/contacts/search",
                params={"q": email, "include_contacts": "true"}
            )
            if isinstance(response, dict):
                contacts = response.get("payload", [])
                if isinstance(contacts, list):
                    for contact in contacts:
                        if contact.get("email") == email:
                            return contact
        except Exception as e:
            logger.debug(f"Failed to search contact by email {email}: {e}")
        return None'''

assert old_find_by_email in content, "Could not find find_contact_by_email"
content = content.replace(old_find_by_email, new_find_by_email, 1)
print("  - Fixed find_contact_by_email")

# ==========================================
# Fix find_contact_by_phone
# ==========================================
old_find_by_phone = '''    async def find_contact_by_phone(
        self,
        phone_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Поиск контакта по номеру телефона.

        Args:
            phone_number: Номер телефона контакта

        Returns:
            Dict с данными контакта или None
        """
        try:
            response = await self._request(
                "GET",
                f"/api/v1/accounts/{self.account_id}/contacts",
                params={"phone_number": phone_number}
            )
            if isinstance(response, dict):
                contacts = response.get("payload", [])
                if isinstance(contacts, list):
                    for contact in contacts:
                        if contact.get("phone_number") == phone_number:
                            return contact
                elif isinstance(contacts, dict) and contacts.get("phone_number") == phone_number:
                    return contacts
        except Exception as e:
            logger.debug(f"Failed to search contact by phone {phone_number}: {e}")
        return None'''

new_find_by_phone = '''    async def find_contact_by_phone(
        self,
        phone_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Поиск контакта по номеру телефона через /contacts/search API.

        Args:
            phone_number: Номер телефона контакта

        Returns:
            Dict с данными контакта или None
        """
        try:
            response = await self._request(
                "GET",
                f"/api/v1/accounts/{self.account_id}/contacts/search",
                params={"q": phone_number, "include_contacts": "true"}
            )
            if isinstance(response, dict):
                contacts = response.get("payload", [])
                if isinstance(contacts, list):
                    for contact in contacts:
                        if contact.get("phone_number") == phone_number:
                            return contact
        except Exception as e:
            logger.debug(f"Failed to search contact by phone {phone_number}: {e}")
        return None'''

assert old_find_by_phone in content, "Could not find find_contact_by_phone"
content = content.replace(old_find_by_phone, new_find_by_phone, 1)
print("  - Fixed find_contact_by_phone")

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\nOK Patched {FILE_PATH}")
print("All three find_contact methods now use /contacts/search API")
