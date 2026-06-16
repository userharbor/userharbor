import pytest
from conftest import VALID_PASSWORD

from userharbor.exceptions import (
    InvalidPasswordError,
    InvalidSessionTokenError,
    WeakPasswordError,
)
from userharbor.security import verify_password

NEW_PASSWORD = "NewStrongpass1!"


def test_change_password_updates_password_hash(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    old_password_hash = store.users[registered_user.username].password_hash
    other_session_token = userharbor.login(
        registered_user.username,
        registered_user.password,
    )

    userharbor.change_password(
        registered_user.username,
        registered_user.password,
        NEW_PASSWORD,
        session_token,
    )

    new_password_hash = store.users[registered_user.username].password_hash
    assert new_password_hash != old_password_hash
    assert not verify_password(registered_user.password, new_password_hash)
    assert verify_password(NEW_PASSWORD, new_password_hash)
    assert store.users[registered_user.username].session_token_hashes == []
    assert not userharbor.verify_session(session_token)
    assert not userharbor.verify_session(other_session_token)


def test_change_password_rejects_invalid_session_token(
    userharbor, store, logged_in_user
) -> None:
    registered_user, _ = logged_in_user
    password_hash_before_change = store.users[registered_user.username].password_hash
    session_token_hashes = store.users[registered_user.username].session_token_hashes
    assert session_token_hashes is not None
    sessions_before_change = session_token_hashes.copy()

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.change_password(
            registered_user.username,
            registered_user.password,
            NEW_PASSWORD,
            "wrong-session-token",
        )

    assert store.users[registered_user.username].password_hash == password_hash_before_change
    assert store.users[registered_user.username].session_token_hashes == sessions_before_change


def test_change_password_rejects_invalid_old_password(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    password_hash_before_change = store.users[registered_user.username].password_hash
    session_token_hashes = store.users[registered_user.username].session_token_hashes
    assert session_token_hashes is not None
    sessions_before_change = session_token_hashes.copy()

    with pytest.raises(InvalidPasswordError, match="Invalid old password"):
        userharbor.change_password(
            registered_user.username,
            "Wrongpass1!",
            NEW_PASSWORD,
            session_token,
        )

    assert store.users[registered_user.username].password_hash == password_hash_before_change
    assert store.users[registered_user.username].session_token_hashes == sessions_before_change


def test_change_password_rejects_weak_new_password(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    password_hash_before_change = store.users[registered_user.username].password_hash
    session_token_hashes = store.users[registered_user.username].session_token_hashes
    assert session_token_hashes is not None
    sessions_before_change = session_token_hashes.copy()

    with pytest.raises(WeakPasswordError, match="Weak new password"):
        userharbor.change_password(
            registered_user.username,
            VALID_PASSWORD,
            "weak",
            session_token,
        )

    assert store.users[registered_user.username].password_hash == password_hash_before_change
    assert store.users[registered_user.username].session_token_hashes == sessions_before_change
