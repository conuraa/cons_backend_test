"""
Pytest configuration and shared fixtures.
"""
import os
import sys
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    test_env = {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASS": "test_pass",
        "ENV": "test",
        "DEBUG": "false",
        "FRONT_SECRET": "test-secret-key",
        "FRONT_BEARER_TOKEN": "test-bearer-token",
        "CHATWOOT_API_URL": "https://chatwoot.test.local",
        "CHATWOOT_API_TOKEN": "test-chatwoot-token",
        "CHATWOOT_ACCOUNT_ID": "1",
        "CHATWOOT_INBOX_ID": "1",
        "CHATWOOT_INBOX_IDENTIFIER": "test-inbox-identifier",
        "ODATA_BASE_URL": "https://odata.test.local",
        "ODATA_BASEURL_CL": "https://odata.test.local",
        "ODATA_USER": "test_odata_user",
        "ODATA_PASSWORD": "test_odata_pass",
        "TELEGRAM_BOT_TOKEN": "123456789:TEST_TOKEN_FOR_TESTING",
        "TELEGRAM_WEBHOOK_URL": "https://webhook.test.local/telegram",
        "RATE_LIMIT_PER_MINUTE": "10000",
        "RATE_LIMIT_CREATE_PER_MINUTE": "1000",
    }
    for key, value in test_env.items():
        os.environ[key] = value
    yield
    for key in test_env:
        os.environ.pop(key, None)


@pytest.fixture(scope="session")
def app():
    """Create FastAPI application instance."""
    from FastAPI.config import get_settings
    get_settings.cache_clear()
    from FastAPI.main import app as fastapi_app
    return fastapi_app


@pytest.fixture
def client(app):
    """Synchronous TestClient."""
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
async def async_client(app):
    """Async TestClient."""
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None),
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    ))
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_chatwoot_client():
    """Mock ChatwootClient."""
    mock = AsyncMock()
    mock.create_conversation.return_value = {"id": 12345, "source_id": "test-source-id", "status": "open"}
    mock.create_contact_via_public_api.return_value = {"id": 1, "source_id": "test-contact-source-id", "pubsub_token": "test-pubsub-token"}
    mock.send_message.return_value = {"id": 1, "content": "Test message"}
    mock.update_conversation.return_value = {"id": 12345, "status": "open"}
    mock.find_contact_by_identifier.return_value = None
    mock.find_contact_by_email.return_value = None
    mock.find_contact_by_phone.return_value = None
    mock.add_conversation_labels.return_value = {"labels": ["test"]}
    mock.find_team_by_name.return_value = 1
    mock.get_teams.return_value = [{"id": 1, "name": "Test Team"}]
    return mock


@pytest.fixture
def mock_onec_client():
    """Mock OneCClient."""
    mock = AsyncMock()
    mock.create_consultation_odata.return_value = {"Ref_Key": "test-ref-key", "Number": "TEST-001"}
    mock.update_consultation_odata.return_value = {"Ref_Key": "test-ref-key"}
    mock.create_client_odata.return_value = {"Ref_Key": "test-client-ref-key"}
    mock.find_client_odata.return_value = None
    return mock


@pytest.fixture
def sample_client_data():
    """Sample client data."""
    return {
        "client_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test Company LLC",
        "contact_name": "John Doe",
        "phone_number": "+998901234567",
        "email": "test@example.com",
        "inn_pinfl": "123456789",
        "code_abonent": "AB001",
        "client_type": "owner",
    }


@pytest.fixture
def sample_consultation_data():
    """Sample consultation data."""
    return {
        "consultation": {
            "question": "Test question",
            "lang": "ru",
            "consultation_type": "Консультация по ведению учёта",
            "importance": 2,
        },
        "client": {
            "phone_number": "+998901234567",
            "contact_name": "John Doe",
            "client_type": "owner",
        },
    }
