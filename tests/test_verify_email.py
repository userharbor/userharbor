import pytest

from userharbor.exceptions import InvalidVerificationTokenError


def test_verify_marks_user_verified(userharbor, store, register_user) -> None:
    registered_user = register_user()

    userharbor.verify_email(registered_user.username, registered_user.verification_code)

    assert store.users[registered_user.username].verified


def test_verify_rejects_invalid_verification_code(
    userharbor, store, register_user
) -> None:
    registered_user = register_user()

    with pytest.raises(
        InvalidVerificationTokenError, match="Invalid verification code"
    ):
        userharbor.verify_email(registered_user.username, "wrong-code")

    assert not store.users[registered_user.username].verified
