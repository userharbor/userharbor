def test_verify_session_accepts_valid_session_token(
    userharbor, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user

    assert userharbor.verify_session(registered_user.username, session_token)


def test_verify_session_rejects_invalid_session_token(
    userharbor, logged_in_user
) -> None:
    registered_user, _ = logged_in_user

    assert not userharbor.verify_session(
        registered_user.username, "wrong-session-token"
    )
