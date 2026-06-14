import pytest
from conftest import VALID_PASSWORD

from userharbor.exceptions import InvalidVerificationTokenError, WeakPasswordError
from userharbor.security import verify_password

NEW_PASSWORD = "ResetStrongpass1!"


def test_reset_password_updates_password_hash(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()
    userharbor.send_password_reset(registered_user.username, registered_user.email)
    reset_token = email_sender.sent_password_resets[0].reset_token
    old_password_hash = store.users[registered_user.username].password_hash

    userharbor.reset_password(registered_user.username, NEW_PASSWORD, reset_token)

    new_password_hash = store.users[registered_user.username].password_hash
    assert new_password_hash != old_password_hash
    assert not verify_password(VALID_PASSWORD, new_password_hash)
    assert verify_password(NEW_PASSWORD, new_password_hash)


def test_reset_password_rejects_invalid_reset_token(
    userharbor, store, register_user
) -> None:
    registered_user = register_user()
    userharbor.send_password_reset(registered_user.username, registered_user.email)
    password_hash_before_reset = store.users[registered_user.username].password_hash

    with pytest.raises(
        InvalidVerificationTokenError, match="Invalid password reset token"
    ):
        userharbor.reset_password(
            registered_user.username,
            NEW_PASSWORD,
            "wrong-reset-token",
        )

    assert store.users[registered_user.username].password_hash == password_hash_before_reset


def test_reset_password_rejects_weak_new_password(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()
    userharbor.send_password_reset(registered_user.username, registered_user.email)
    reset_token = email_sender.sent_password_resets[0].reset_token
    password_hash_before_reset = store.users[registered_user.username].password_hash

    with pytest.raises(WeakPasswordError, match="Weak new password"):
        userharbor.reset_password(registered_user.username, "weak", reset_token)

    assert store.users[registered_user.username].password_hash == password_hash_before_reset
