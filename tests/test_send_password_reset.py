from datetime import timedelta

import pytest
from conftest import SECRET_KEY

from userharbor.exceptions import InvalidEmailError
from userharbor.security import verify_token
from userharbor.utils import utcnow


def test_send_password_reset_stores_token_hash_and_sends_email(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()

    before_send = utcnow()

    userharbor.send_password_reset(registered_user.email)

    after_send = utcnow()

    sent_password_reset = email_sender.sent_password_resets[0]
    password_reset_token_hash = store.users[
        registered_user.username
    ].password_reset_token_hash
    assert password_reset_token_hash is not None
    password_reset = store.get_password_reset(password_reset_token_hash)
    assert password_reset is not None

    assert sent_password_reset.username == registered_user.username
    assert sent_password_reset.email == registered_user.email
    assert verify_token(
        sent_password_reset.reset_token,
        password_reset.token_hash,
        SECRET_KEY,
    )
    assert password_reset.username == registered_user.username
    assert before_send + timedelta(hours=1) <= password_reset.expires_at
    assert password_reset.expires_at <= after_send + timedelta(hours=1)


def test_send_password_reset_rejects_invalid_email(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()

    with pytest.raises(InvalidEmailError, match="Invalid email"):
        userharbor.send_password_reset("wrong@example.com")

    assert store.users[registered_user.username].password_reset_token_hash is None
    assert email_sender.sent_password_resets == []
