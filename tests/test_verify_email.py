from datetime import timedelta

import pytest

from userharbor.exceptions import InvalidVerificationTokenError
from userharbor.utils import utcnow


def test_verify_marks_user_verified_and_sends_email_verified_notification(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()
    verification_token_hash = store.users[
        registered_user.username
    ].email_verification_token_hash

    userharbor.verify_email(registered_user.verification_token)

    assert store.users[registered_user.username].verified
    assert store.get_email_verification(verification_token_hash) is None
    assert len(email_sender.sent_email_verified) == 1
    sent_email_verified = email_sender.sent_email_verified[0]
    assert sent_email_verified.username == registered_user.username
    assert sent_email_verified.email == registered_user.email


def test_verify_accepts_naive_utc_expiration(userharbor, store, register_user) -> None:
    registered_user = register_user()
    verification_token_hash = store.users[
        registered_user.username
    ].email_verification_token_hash
    verification = store.email_verifications[verification_token_hash]
    verification.expires_at = verification.expires_at.replace(tzinfo=None)

    userharbor.verify_email(registered_user.verification_token)

    assert store.users[registered_user.username].verified
    assert store.get_email_verification(verification_token_hash) is None


def test_verify_rejects_invalid_verification_token(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()

    with pytest.raises(
        InvalidVerificationTokenError, match="Invalid verification token"
    ):
        userharbor.verify_email("wrong-code")

    assert not store.users[registered_user.username].verified
    assert email_sender.sent_email_verified == []


def test_verify_rejects_expired_verification_token(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()
    verification_token_hash = store.users[
        registered_user.username
    ].email_verification_token_hash
    store.email_verifications[verification_token_hash].expires_at = (
        utcnow() - timedelta(seconds=1)
    )

    with pytest.raises(
        InvalidVerificationTokenError, match="Verification token expired"
    ):
        userharbor.verify_email(registered_user.verification_token)

    assert not store.users[registered_user.username].verified
    assert store.get_email_verification(verification_token_hash) is None
    assert email_sender.sent_email_verified == []
