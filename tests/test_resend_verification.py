from datetime import datetime, timedelta

import pytest
from conftest import SECRET_KEY, VALID_EMAIL, VALID_USERNAME

from userharbor.exceptions import InvalidUsernameError, UserAlreadyVerifiedError
from userharbor.security import verify_token


def test_resend_verification_replaces_token_hash_and_sends_email(
    userharbor, store, email_sender, register_user
) -> None:
    registered_user = register_user()
    old_verification_token_hash = store.users[
        registered_user.username
    ].email_verification_token_hash

    before_resend = datetime.now()

    userharbor.resend_verification(registered_user.username, registered_user.email)

    after_resend = datetime.now()

    sent_verification = email_sender.sent_verifications[-1]
    new_verification_token_hash = store.users[
        registered_user.username
    ].email_verification_token_hash

    assert len(email_sender.sent_verifications) == 2
    assert sent_verification.username == registered_user.username
    assert sent_verification.email == registered_user.email
    assert new_verification_token_hash != old_verification_token_hash
    assert store.get_email_verification(old_verification_token_hash) is None
    assert verify_token(
        sent_verification.verification_token,
        new_verification_token_hash,
        SECRET_KEY,
    )
    verification = store.get_email_verification(new_verification_token_hash)
    assert verification is not None
    assert verification.username == registered_user.username
    assert before_resend + timedelta(hours=24) <= verification.expires_at
    assert verification.expires_at <= after_resend + timedelta(hours=24)


@pytest.mark.parametrize(
    ("username", "email"),
    [
        ("unknown", VALID_EMAIL),
        (VALID_USERNAME, "wrong@example.com"),
    ],
)
def test_resend_verification_rejects_invalid_username_or_email(
    userharbor, store, email_sender, register_user, username, email
) -> None:
    registered_user = register_user()
    verification_token_hash = store.users[
        registered_user.username
    ].email_verification_token_hash

    with pytest.raises(InvalidUsernameError, match="Invalid username or email"):
        userharbor.resend_verification(username, email)

    assert len(email_sender.sent_verifications) == 1
    assert (
        store.users[registered_user.username].email_verification_token_hash
        == verification_token_hash
    )
    assert store.get_email_verification(verification_token_hash) is not None


def test_resend_verification_rejects_verified_user(
    userharbor, store, email_sender, verified_user
) -> None:
    with pytest.raises(UserAlreadyVerifiedError, match="User already verified"):
        userharbor.resend_verification(verified_user.username, verified_user.email)

    assert len(email_sender.sent_verifications) == 1
    assert store.email_verifications == {}
