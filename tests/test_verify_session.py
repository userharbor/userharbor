from datetime import timedelta

from conftest import SECRET_KEY, VALID_EMAIL, VALID_PASSWORD, VALID_USERNAME

from userharbor.main import UserHarbor
from userharbor.utils import utcnow


def create_logged_in_userharbor(store, email_sender, **kwargs):
    userharbor = UserHarbor(SECRET_KEY, store, email_sender, **kwargs)
    userharbor.register(VALID_USERNAME, VALID_EMAIL, VALID_PASSWORD)
    verification_token = email_sender.sent_verifications[-1].verification_token
    userharbor.verify_email(verification_token)
    session_token = userharbor.login(VALID_USERNAME, VALID_PASSWORD)
    session_token_hash = store.users[VALID_USERNAME].session_token_hashes[-1]
    return userharbor, session_token, session_token_hash


def test_verify_session_accepts_valid_session_token(userharbor, logged_in_user) -> None:
    _, session_token = logged_in_user

    assert userharbor.verify_session(session_token)


def test_verify_session_rejects_invalid_session_token(
    userharbor, logged_in_user
) -> None:
    _ = logged_in_user

    assert not userharbor.verify_session("wrong-session-token")


def test_verify_session_removes_expired_session(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    session_token_hash = store.users[registered_user.username].session_token_hashes[-1]
    store.sessions[session_token_hash].expires_at = utcnow() - timedelta(days=1)

    assert not userharbor.verify_session(session_token)
    assert store.users[registered_user.username].session_token_hashes == []
    assert store.get_session(session_token_hash) is None


def test_verify_session_refreshes_session_near_expiration(
    store, email_sender
) -> None:
    session_token_ttl = timedelta(days=10)
    userharbor, session_token, session_token_hash = create_logged_in_userharbor(
        store,
        email_sender,
        session_token_ttl=session_token_ttl,
        sesion_refresh_threshold=timedelta(days=7),
    )
    store.sessions[session_token_hash].expires_at = utcnow() + timedelta(days=1)

    before_verify = utcnow()

    assert userharbor.verify_session(session_token)

    after_verify = utcnow()
    session = store.get_session(session_token_hash)
    assert session is not None
    assert before_verify + session_token_ttl <= session.expires_at
    assert session.expires_at <= after_verify + session_token_ttl


def test_verify_session_does_not_refresh_session_outside_threshold(
    store, email_sender
) -> None:
    userharbor, session_token, session_token_hash = create_logged_in_userharbor(
        store,
        email_sender,
        session_token_ttl=timedelta(days=10),
        sesion_refresh_threshold=timedelta(days=7),
    )
    original_expires_at = utcnow() + timedelta(days=8)
    store.sessions[session_token_hash].expires_at = original_expires_at

    assert userharbor.verify_session(session_token)

    session = store.get_session(session_token_hash)
    assert session is not None
    assert session.expires_at == original_expires_at


def test_verify_session_does_not_refresh_session_when_threshold_is_none(
    store, email_sender
) -> None:
    userharbor, session_token, session_token_hash = create_logged_in_userharbor(
        store,
        email_sender,
        session_token_ttl=timedelta(days=10),
        sesion_refresh_threshold=None,
    )
    original_expires_at = utcnow() + timedelta(days=1)
    store.sessions[session_token_hash].expires_at = original_expires_at

    assert userharbor.verify_session(session_token)

    session = store.get_session(session_token_hash)
    assert session is not None
    assert session.expires_at == original_expires_at
