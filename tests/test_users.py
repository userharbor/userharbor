from dataclasses import dataclass

import pytest
from fakes import InMemoryUserStore

from userharbor import UserHarbor


@pytest.mark.parametrize("verified", [False, True])
def test_users_get_by_email_returns_user(userharbor, register_user, verified) -> None:
    registered_user = register_user()
    if verified:
        userharbor.verify_email(registered_user.verification_token)

    user = userharbor.users.get_by_email(registered_user.email)

    assert user is not None
    assert user.username == registered_user.username
    assert user.email == registered_user.email
    assert user.verified is verified


def test_users_get_by_email_returns_none_for_missing_user(userharbor) -> None:
    assert userharbor.users.get_by_email("missing@example.com") is None


def test_users_get_by_email_normalizes_email(userharbor, register_user) -> None:
    register_user(email="Alice@Example.com")

    user = userharbor.users.get_by_email("ALICE@EXAMPLE.COM")

    assert user is not None
    assert user.email == "alice@example.com"


@pytest.mark.parametrize("verified", [False, True])
def test_users_get_by_username_returns_user(
    userharbor, register_user, verified
) -> None:
    registered_user = register_user()
    if verified:
        userharbor.verify_email(registered_user.verification_token)

    user = userharbor.users.get_by_username(registered_user.username)

    assert user is not None
    assert user.username == registered_user.username
    assert user.email == registered_user.email
    assert user.verified is verified


def test_users_get_by_username_returns_none_for_missing_user(userharbor) -> None:
    assert userharbor.users.get_by_username("missing") is None


@pytest.mark.parametrize(
    ("username", "lookup"), [("Alice", "aLiCe"), ("Straße", "STRASSE")]
)
def test_users_get_by_username_is_case_insensitive(
    userharbor, register_user, username, lookup
) -> None:
    register_user(username=username)

    user = userharbor.users.get_by_username(lookup)

    assert user is not None
    assert user.username == username


def test_users_get_by_username_preserves_custom_user(email_sender) -> None:
    @dataclass
    class CustomUser:
        username: str
        email: str
        verified: bool
        display_name: str

    class CustomUserStore(InMemoryUserStore):
        def get_user_by_username(self, username: str) -> CustomUser | None:  # ty: ignore
            user = super().get_user_by_username(username)
            if user is None:
                return None
            return CustomUser(
                user.username, user.email, user.verified, display_name="Alice"
            )

    harbor = UserHarbor("test-secret-key", CustomUserStore(), email_sender)
    harbor.register("alice", "alice@example.com", "Strongpass1!")

    user = harbor.users.get_by_username("alice")

    assert isinstance(user, CustomUser)
    assert user.display_name == "Alice"
