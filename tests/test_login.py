import pytest
from conftest import SECRET_KEY

from userharbor.exceptions import InvalidPasswordError, UnverifiedUserError
from userharbor.security import verify_token


def test_login_creates_session_for_verified_user(
    userharbor, store, verified_user
) -> None:
    session_token = userharbor.login(verified_user.username, verified_user.password)

    session_token_hashes = store.users[verified_user.username].session_token_hashes
    assert session_token_hashes is not None
    assert len(session_token_hashes) == 1
    assert verify_token(session_token, session_token_hashes[0], SECRET_KEY)


def test_login_rejects_invalid_password(userharbor, store, verified_user) -> None:
    with pytest.raises(InvalidPasswordError, match="Invalid password"):
        userharbor.login(verified_user.username, "Wrongpass1!")

    assert store.users[verified_user.username].session_token_hashes == []


def test_login_rejects_unverified_user(userharbor, store, register_user) -> None:
    registered_user = register_user()

    with pytest.raises(UnverifiedUserError, match="User email not verified"):
        userharbor.login(registered_user.username, registered_user.password)

    assert store.users[registered_user.username].session_token_hashes == []
