import pytest
from conftest import (
    SECRET_KEY,
    VALID_EMAIL,
    VALID_PASSWORD,
    VALID_USERNAME,
)

from userharbor.exceptions import (
    InvalidEmailError,
    InvalidUsernameError,
    WeakPasswordError,
)
from userharbor.security import verify_password, verify_token


def test_register_creates_user_and_sends_verification(
    userharbor, store, email_sender
) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)

    stored_user = store.users[VALID_USERNAME]
    sent_verification = email_sender.sent_verifications[0]

    assert stored_user.username == VALID_USERNAME
    assert stored_user.email == VALID_EMAIL
    assert stored_user.password_hash != VALID_PASSWORD
    assert verify_password(VALID_PASSWORD, stored_user.password_hash)
    assert not stored_user.verified

    assert sent_verification.username == VALID_USERNAME
    assert sent_verification.email == VALID_EMAIL
    assert verify_token(
        sent_verification.verification_code,
        stored_user.email_verification_code_hash,
        SECRET_KEY,
    )


@pytest.mark.parametrize(
    "username",
    [
        "ab",
        "janek_123",
    ],
)
def test_register_rejects_invalid_username(
    userharbor, store, email_sender, username
) -> None:
    with pytest.raises(InvalidUsernameError, match="Invalid username"):
        userharbor.register(username, VALID_EMAIL, VALID_PASSWORD)

    assert store.users == {}
    assert email_sender.sent_verifications == []


def test_register_rejects_invalid_email(userharbor, store, email_sender) -> None:
    with pytest.raises(InvalidEmailError, match="Invalid email"):
        userharbor.register(VALID_USERNAME, "not-an-email", VALID_PASSWORD)

    assert store.users == {}
    assert email_sender.sent_verifications == []


@pytest.mark.parametrize(
    "password",
    [
        "Short1!",
        "nouppercase1!",
        "NOLOWERCASE1!",
        "NoNumber!",
        "NoSpecial1",
    ],
)
def test_register_rejects_weak_password(
    userharbor, store, email_sender, password
) -> None:
    with pytest.raises(WeakPasswordError, match="Weak password"):
        userharbor.register(VALID_USERNAME, VALID_EMAIL, password)

    assert store.users == {}
    assert email_sender.sent_verifications == []
