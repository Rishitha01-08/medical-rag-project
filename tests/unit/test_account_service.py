from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.services import account_service


def test_account_login_session_encrypted_history_and_delete(monkeypatch):
    database_path = Path("data/local") / f"account-test-{uuid4().hex}.sqlite3"
    monkeypatch.setattr(
        account_service,
        "settings",
        replace(
            account_service.settings,
            database_path=str(database_path),
            database_url="",
            data_encryption_key=Fernet.generate_key().decode("ascii"),
        ),
    )
    try:
        account_service.initialize_account_store()
        user = account_service.create_account("Person@Example.org", "long test password 123")

        assert user["email"] == "person@example.org"
        assert account_service.authenticate("PERSON@example.org", "long test password 123")["id"] == user["id"]
        assert account_service.authenticate("person@example.org", "wrong password") is None
        with pytest.raises(ValueError, match="already exists"):
            account_service.create_account("person@example.org", "long test password 123")

        token = account_service.create_session(user["id"])
        assert account_service.get_user_for_session(token)["id"] == user["id"]
        account_service.save_conversation(user["id"], "private question", {"answer": "private response"})
        assert account_service.list_conversations(user["id"]) == []

        account_service.set_history_enabled(user["id"], True)
        account_service.save_conversation(user["id"], "private question", {"answer": "private response"})
        saved = account_service.list_conversations(user["id"])
        assert saved[0]["question"] == "private question"
        assert saved[0]["result"]["answer"] == "private response"

        account_service.set_history_enabled(user["id"], False)
        assert account_service.list_conversations(user["id"]) == []
        account_service.revoke_session(token)
        assert account_service.get_user_for_session(token) is None
        account_service.delete_account(user["id"])
        assert account_service.authenticate("person@example.org", "long test password 123") is None
    finally:
        database_path.unlink(missing_ok=True)
