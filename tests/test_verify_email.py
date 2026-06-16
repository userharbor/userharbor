from datetime import datetime, timedelta

import pytest

from userharbor.exceptions import InvalidVerificationTokenError


def test_verify_marks_user_verified(userharbor, store, register_user) -> None:
    registered_user = register_user()
    verification_token_hash = store.users[
        registered_user.username
    ].email_verification_token_hash

    userharbor.verify_email(registered_user.verification_token)

    assert store.users[registered_user.username].verified
    assert store.get_email_verification(verification_token_hash) is None


def test_verify_rejects_invalid_verification_token(
    userharbor, store, register_user
) -> None:
    registered_user = register_user()

    with pytest.raises(
        InvalidVerificationTokenError, match="Invalid verification token"
    ):
        userharbor.verify_email("wrong-code")

    assert not store.users[registered_user.username].verified


def test_verify_rejects_expired_verification_token(
    userharbor, store, register_user
) -> None:
    registered_user = register_user()
    verification_token_hash = store.users[
        registered_user.username
    ].email_verification_token_hash
    store.email_verifications[
        verification_token_hash
    ].expires_at = datetime.now() - timedelta(seconds=1)

    with pytest.raises(
        InvalidVerificationTokenError, match="Verification token expired"
    ):
        userharbor.verify_email(registered_user.verification_token)

    assert not store.users[registered_user.username].verified
    assert store.get_email_verification(verification_token_hash) is None
