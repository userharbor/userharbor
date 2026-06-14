import pytest
from conftest import (
    SECRET_KEY,
    VALID_EMAIL,
    VALID_PASSWORD,
    VALID_USERNAME,
)

from userharbor.exceptions import InvalidPasswordError, UnverifiedUserError
from userharbor.security import verify_token


def test_login_creates_session_for_verified_user(
    userharbor, store, email_sender
) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)
    verification_code = email_sender.sent_verifications[0].verification_code
    userharbor.verify_email(VALID_USERNAME, verification_code)

    session_token = userharbor.login(VALID_USERNAME, VALID_PASSWORD)

    session_token_hashes = store.users[VALID_USERNAME].session_token_hashes
    assert session_token_hashes is not None
    assert len(session_token_hashes) == 1
    assert verify_token(session_token, session_token_hashes[0], SECRET_KEY)


def test_login_rejects_invalid_password(userharbor, store) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)
    store.set_user_verified(VALID_USERNAME)

    with pytest.raises(InvalidPasswordError, match="Invalid password"):
        userharbor.login(VALID_USERNAME, "Wrongpass1!")

    assert store.users[VALID_USERNAME].session_token_hashes == []


def test_login_rejects_unverified_user(userharbor, store) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)

    with pytest.raises(UnverifiedUserError, match="User email not verified"):
        userharbor.login(VALID_USERNAME, VALID_PASSWORD)

    assert store.users[VALID_USERNAME].session_token_hashes == []
