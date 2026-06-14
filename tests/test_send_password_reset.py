import pytest
from conftest import SECRET_KEY, VALID_EMAIL, VALID_USERNAME

from userharbor.exceptions import InvalidUsernameError
from userharbor.security import verify_token


def test_send_password_reset_stores_token_hash_and_sends_email(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()

    userharbor.send_password_reset(registered_user.username, registered_user.email)

    sent_password_reset = email_sender.sent_password_resets[0]
    assert sent_password_reset.username == registered_user.username
    assert sent_password_reset.email == registered_user.email
    assert verify_token(
        sent_password_reset.reset_token,
        store.users[registered_user.username].password_reset_token_hash,
        SECRET_KEY,
    )


@pytest.mark.parametrize(
    ("username", "email"),
    [
        ("unknown", VALID_EMAIL),
        (VALID_USERNAME, "wrong@example.com"),
    ],
)
def test_send_password_reset_rejects_invalid_username_or_email(
    userharbor, store, email_sender, register_user, username, email
) -> None:
    registered_user = register_user()

    with pytest.raises(InvalidUsernameError, match="Invalid username or email"):
        userharbor.send_password_reset(username, email)

    assert store.users[registered_user.username].password_reset_token_hash is None
    assert email_sender.sent_password_resets == []
