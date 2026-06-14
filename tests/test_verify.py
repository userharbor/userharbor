import pytest
from conftest import (
    VALID_EMAIL,
    VALID_PASSWORD,
    VALID_USERNAME,
)

from userharbor.exceptions import InvalidVerificationCodeError


def test_verify_marks_user_verified(userharbor, store, email_sender) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)
    verification_code = email_sender.sent_verifications[0].verification_code

    userharbor.verify_email(VALID_USERNAME, verification_code)

    assert store.users[VALID_USERNAME].verified


def test_verify_rejects_invalid_verification_code(userharbor, store) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)

    with pytest.raises(InvalidVerificationCodeError, match="Invalid verification code"):
        userharbor.verify_email(VALID_USERNAME, "wrong-code")

    assert not store.users[VALID_USERNAME].verified
