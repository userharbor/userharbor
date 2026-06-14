from conftest import VALID_EMAIL, VALID_PASSWORD, VALID_USERNAME


def test_verify_session_accepts_valid_session_token(
    userharbor, store, email_sender
) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)
    verification_code = email_sender.sent_verifications[0].verification_code
    userharbor.verify_email(VALID_USERNAME, verification_code)
    session_token = userharbor.login(VALID_USERNAME, VALID_PASSWORD)

    assert userharbor.verify_session(VALID_USERNAME, session_token)


def test_verify_session_rejects_invalid_session_token(
    userharbor, store, email_sender
) -> None:
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)
    verification_code = email_sender.sent_verifications[0].verification_code
    userharbor.verify_email(VALID_USERNAME, verification_code)
    userharbor.login(VALID_USERNAME, VALID_PASSWORD)

    assert not userharbor.verify_session(VALID_USERNAME, "wrong-session-token")
