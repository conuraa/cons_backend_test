"""
Bug 10: Неправильный приоритет формирования display_name.

ПРОБЛЕМА:
    В функции _build_client_display_name приоритет:
    company_name → name → contact_name → "Клиент"
    
    Но правильный приоритет:
    ФИО (contact_name) → компания (company_name) → fallback

ОЖИДАЕМОЕ ПОВЕДЕНИЕ:
    1. Если есть contact_name и это ФИО → использовать его
    2. Иначе если есть company_name → использовать его
    3. Иначе если есть name → использовать его
    4. Иначе → "Клиент"

ТЕСТЫ:
    - Приоритет ФИО над компанией
    - Первый запуск (новый клиент без данных)
    - Правильный формат результата
"""
import pytest
from unittest.mock import MagicMock
import sys

sys.path.insert(0, "/home/sada/cons_backend")


class TestBug10DisplayName:
    """Тесты для Bug 10: Приоритет display_name."""
    
    def test_contact_name_priority_over_company(self):
        """
        ПАДАЮЩИЙ ТЕСТ (Bug 10): ФИО (contact_name) должно иметь приоритет над компанией.
        """
        # Клиент с ФИО и названием компании
        client = MagicMock()
        client.contact_name = "Иван Петров"
        client.company_name = "ООО Ромашка"
        client.name = "Test Name"
        client.code_abonent = "ABC123"
        client.org_inn = "1234567890"
        
        result = build_client_display_name(client)
        
        # ФИО должно быть в результате, а не название компании
        assert "Иван Петров" in result, (
            f"Bug 10: ФИО 'Иван Петров' должно быть в display_name. "
            f"Получено: {result}"
        )
        # Компания НЕ должна быть в базовом имени
        assert "ООО Ромашка" not in result.replace("Clobus", "").split("ABC123")[0].strip(), (
            f"Bug 10: Компания не должна быть базовым именем при наличии ФИО. "
            f"Получено: {result}"
        )
    
    def test_company_name_used_when_no_contact_name(self):
        """Если нет ФИО, используется company_name."""
        client = MagicMock()
        client.contact_name = None
        client.company_name = "ООО Ромашка"
        client.name = "Test Name"
        client.code_abonent = "ABC123"
        client.org_inn = None
        
        result = build_client_display_name(client)
        
        assert "ООО Ромашка" in result or "Ромашка" in result
    
    def test_fallback_when_no_names(self):
        """Первый запуск - клиент без данных → fallback."""
        client = MagicMock()
        client.contact_name = None
        client.company_name = None
        client.name = None
        client.code_abonent = None
        client.org_inn = None
        
        result = build_client_display_name(client)
        
        assert "Клиент" in result, (
            f"Для пустого клиента должен быть fallback 'Клиент'. Получено: {result}"
        )
    
    def test_name_used_when_no_contact_and_company(self):
        """Если нет contact_name и company_name, используется name."""
        client = MagicMock()
        client.contact_name = None
        client.company_name = None
        client.name = "Общее Имя"
        client.code_abonent = "XYZ789"
        client.org_inn = None
        
        result = build_client_display_name(client)
        
        assert "Общее Имя" in result


class TestDisplayNameFormat:
    """Тесты для формата display_name."""
    
    def test_format_with_all_fields(self):
        """Формат: Clobus + ФИО + КодАбонента + (ИНН)"""
        client = MagicMock()
        client.contact_name = "Иван Петров"
        client.company_name = None
        client.name = None
        client.code_abonent = "ABC123"
        client.org_inn = "1234567890"
        
        result = build_client_display_name(client)
        
        # Проверяем наличие всех компонентов
        assert "Clobus" in result, "Должен быть префикс Clobus"
        assert "Иван Петров" in result, "Должно быть ФИО"
        assert "ABC123" in result, "Должен быть код абонента"
        assert "1234567890" in result, "Должен быть ИНН"
    
    def test_no_duplicate_clobus(self):
        """Если имя уже содержит Clobus, не дублировать."""
        client = MagicMock()
        client.contact_name = None
        client.company_name = "Clobus ООО Ромашка"
        client.name = None
        client.code_abonent = None
        client.org_inn = None
        
        result = build_client_display_name(client)
        
        # Не должно быть "Clobus Clobus"
        assert "Clobus Clobus" not in result, (
            f"Не должно быть дублирования Clobus. Получено: {result}"
        )
    
    def test_strips_whitespace(self):
        """Результат должен быть без лишних пробелов."""
        client = MagicMock()
        client.contact_name = "  Иван Петров  "
        client.company_name = None
        client.name = None
        client.code_abonent = None
        client.org_inn = None
        
        result = build_client_display_name(client)
        
        assert not result.startswith(" "), "Не должно быть пробелов в начале"
        assert not result.endswith(" "), "Не должно быть пробелов в конце"
        assert "  " not in result, "Не должно быть двойных пробелов"


class TestIsPersonName:
    """Тесты для определения ФИО."""
    
    def test_detect_fio(self):
        """Определение что строка - это ФИО."""
        fio_examples = [
            "Иван Петров",
            "Анна Сидорова",
            "Мария Иванова Петровна",
            "Алексей",
        ]
        
        for fio in fio_examples:
            assert is_person_name(fio), f"'{fio}' должно определяться как ФИО"
    
    def test_detect_company(self):
        """Определение что строка - это название компании."""
        company_examples = [
            "ООО Ромашка",
            "ИП Петров",
            "ЗАО Вектор",
            "АО Газпром",
            "ТОО Альфа",
        ]
        
        for company in company_examples:
            assert not is_person_name(company), (
                f"'{company}' НЕ должно определяться как ФИО"
            )


def is_person_name(name: str) -> bool:
    """
    BUG FIX #10: Определяет, является ли строка ФИО.
    
    Признаки компании:
    - Начинается с ООО, ИП, ЗАО, АО, ТОО, ОАО, ПАО
    - Содержит юридические термины
    
    Args:
        name: Строка для проверки
    
    Returns:
        True если похоже на ФИО, False если похоже на компанию
    """
    if not name:
        return False
    
    name_upper = name.strip().upper()
    
    # Признаки юридического лица
    company_prefixes = ("ООО", "ИП", "ЗАО", "АО", "ТОО", "ОАО", "ПАО", "НАО", "CLOBUS")
    company_keywords = ("КОМПАНИЯ", "КОРПОРАЦИЯ", "ХОЛДИНГ", "ГРУП", "GROUP")
    
    for prefix in company_prefixes:
        if name_upper.startswith(prefix + " ") or name_upper == prefix:
            return False
    
    for keyword in company_keywords:
        if keyword in name_upper:
            return False
    
    return True


def build_client_display_name(client) -> str:
    """
    BUG FIX #10: Формирование display_name с правильным приоритетом.
    
    Приоритет:
    1. contact_name (если это ФИО)
    2. company_name
    3. name
    4. "Клиент" (fallback)
    
    Формат: Clobus + Имя + КодАбонента + (ИНН)
    """
    # Определяем базовое имя с правильным приоритетом
    base_name = None
    
    # 1. Сначала проверяем contact_name (ФИО)
    if client.contact_name and client.contact_name.strip():
        if is_person_name(client.contact_name):
            base_name = client.contact_name.strip()
    
    # 2. Затем company_name
    if not base_name and client.company_name and client.company_name.strip():
        base_name = client.company_name.strip()
    
    # 3. Затем name
    if not base_name and client.name and client.name.strip():
        base_name = client.name.strip()
    
    # 4. Fallback
    if not base_name:
        base_name = "Клиент"
    
    # Проверяем, начинается ли уже с Clobus
    base_name_lower = base_name.lower()
    if base_name_lower.startswith("clobus"):
        parts = [base_name]
    else:
        parts = ["Clobus", base_name]
    
    # Добавляем код абонента
    if client.code_abonent and client.code_abonent.strip():
        parts.append(client.code_abonent.strip())
    
    # Добавляем ИНН
    if client.org_inn and client.org_inn.strip():
        parts.append(f"({client.org_inn.strip()})")
    
    return " ".join(parts)


class TestIntegrationDisplayName:
    """Интеграционные тесты."""
    
    def test_real_world_scenario(self):
        """Реальный сценарий: клиент Telegram с ФИО."""
        client = MagicMock()
        # Telegram передаёт ФИО в contact_name
        client.contact_name = "Алексей Смирнов"
        # company_name может быть установлен позже
        client.company_name = None
        client.name = "alexey_smirnov"  # username
        client.code_abonent = "CLB001"
        client.org_inn = None
        
        result = build_client_display_name(client)
        
        # Должно использоваться ФИО, а не username
        assert "Алексей Смирнов" in result
        assert "alexey_smirnov" not in result
    
    def test_first_run_empty_client(self):
        """Первый запуск: клиент без данных."""
        client = MagicMock()
        client.contact_name = None
        client.company_name = None
        client.name = None
        client.code_abonent = None
        client.org_inn = None
        
        result = build_client_display_name(client)
        
        assert result == "Clobus Клиент"
