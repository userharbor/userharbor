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


def test_reset_password_removes_sessions_and_reset_token(
    userharbor, store, email_sender, verified_user
) -> None:
    first_session_token = userharbor.login(
        verified_user.username, verified_user.password
    )
    second_session_token = userharbor.login(
        verified_user.username, verified_user.password
    )
    userharbor.send_password_reset(verified_user.username, verified_user.email)
    reset_token = email_sender.sent_password_resets[0].reset_token

    userharbor.reset_password(verified_user.username, NEW_PASSWORD, reset_token)

    assert store.users[verified_user.username].session_token_hashes == []
    assert store.users[verified_user.username].password_reset_token_hash is None
    assert not userharbor.verify_session(first_session_token)
    assert not userharbor.verify_session(second_session_token)


def test_reset_password_rejects_invalid_reset_token(
    userharbor, store, register_user
) -> None:
    registered_user = register_user()
    userharbor.send_password_reset(registered_user.username, registered_user.email)
    password_hash_before_reset = store.users[registered_user.username].password_hash
    reset_token_hash = store.users[registered_user.username].password_reset_token_hash

    with pytest.raises(
        InvalidVerificationTokenError, match="Invalid password reset token"
    ):
        userharbor.reset_password(
            registered_user.username,
            NEW_PASSWORD,
            "wrong-reset-token",
        )

    assert store.users[registered_user.username].password_hash == password_hash_before_reset
    assert store.users[registered_user.username].password_reset_token_hash == reset_token_hash


def test_reset_password_rejects_weak_new_password(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()
    userharbor.send_password_reset(registered_user.username, registered_user.email)
    reset_token = email_sender.sent_password_resets[0].reset_token
    password_hash_before_reset = store.users[registered_user.username].password_hash
    reset_token_hash = store.users[registered_user.username].password_reset_token_hash

    with pytest.raises(WeakPasswordError, match="Weak new password"):
        userharbor.reset_password(registered_user.username, "weak", reset_token)

    assert store.users[registered_user.username].password_hash == password_hash_before_reset
    assert store.users[registered_user.username].password_reset_token_hash == reset_token_hash
