import pytest
from conftest import VALID_EMAIL, VALID_PASSWORD, VALID_USERNAME

from userharbor.exceptions import InvalidSessionTokenError


def test_logout_removes_valid_session(userharbor, store, email_sender) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)
    verification_code = email_sender.sent_verifications[0].verification_code
    userharbor.verify_email(VALID_USERNAME, verification_code)
    session_token = userharbor.login(VALID_USERNAME, VALID_PASSWORD)

    userharbor.logout(VALID_USERNAME, session_token)

    assert store.users[VALID_USERNAME].session_token_hashes == []


def test_logout_rejects_invalid_session_token(userharbor, store, email_sender) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)
    verification_code = email_sender.sent_verifications[0].verification_code
    userharbor.verify_email(VALID_USERNAME, verification_code)
    userharbor.login(VALID_USERNAME, VALID_PASSWORD)
    session_token_hashes = store.users[VALID_USERNAME].session_token_hashes
    assert session_token_hashes is not None
    sessions_before_logout = session_token_hashes.copy()

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.logout(VALID_USERNAME, "wrong-session-token")

    assert store.users[VALID_USERNAME].session_token_hashes == sessions_before_logout
