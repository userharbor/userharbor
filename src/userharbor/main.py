from datetime import timedelta
from typing import Generic

from .exceptions import (
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidPasswordResetTokenError,
    InvalidSessionTokenError,
    InvalidUsernameError,
    InvalidVerificationTokenError,
    UnverifiedUserError,
    WeakPasswordError,
)
from .interfaces import CreateUserRequest, EmailSender, UserStore, UserT, UserToken
from .security import (
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from .utils import as_aware_utc, utcnow
from .validations import is_email_valid, is_password_strong, is_username_valid


class UserHarbor(Generic[UserT]):
    def __init__(
        self,
        secret_key: str,
        store: UserStore[UserT],
        email_sender: EmailSender,
        email_verification_token_ttl: timedelta = timedelta(hours=24),
        password_reset_token_ttl: timedelta = timedelta(hours=1),
        session_token_ttl: timedelta = timedelta(days=30),
        session_refresh_threshold: timedelta | None = timedelta(days=7),
    ) -> None:
        self._secret_key = secret_key
        self._store = store
        self._email_sender = email_sender
        self._email_verification_token_ttl = email_verification_token_ttl
        self._password_reset_token_ttl = password_reset_token_ttl
        self._session_token_ttl = session_token_ttl
        self._session_refresh_threshold = session_refresh_threshold

    def register(self, username: str, email: str, password: str) -> None:
        if not is_username_valid(username):
            raise InvalidUsernameError("Invalid username")
        if not is_email_valid(email):
            raise InvalidEmailError("Invalid email")
        if not is_password_strong(password):
            raise WeakPasswordError("Weak password")

        verification_token = generate_token()
        self._store.create_user(
            CreateUserRequest(
                username=username,
                email=email,
                password_hash=hash_password(password),
                verification_token_hash=hash_token(
                    verification_token, self._secret_key
                ),
                expires_at=utcnow() + self._email_verification_token_ttl,
            )
        )
        self._email_sender.send_verification(username, email, verification_token)

    def verify_email(self, verification_token: str) -> None:
        with self._store.transaction():
            verification = self._store.get_email_verification(
                hash_token(verification_token, self._secret_key)
            )
            if not verification:
                raise InvalidVerificationTokenError("Invalid verification token")
            if utcnow() > as_aware_utc(verification.expires_at):
                self._store.remove_email_verification(verification.token_hash)
                raise InvalidVerificationTokenError("Verification token expired")
            self._store.remove_email_verification(verification.token_hash)
            self._store.set_user_verified(verification.username)

    def resend_verification(self, email: str) -> None:
        user = self._store.get_user_by_email(email)
        if not user or user.verified:
            return
        verification_token = generate_token()
        self._store.set_email_verification(
            UserToken(
                username=user.username,
                token_hash=hash_token(verification_token, self._secret_key),
                expires_at=utcnow() + self._email_verification_token_ttl,
            )
        )
        self._email_sender.send_verification(user.username, email, verification_token)

    def login(self, username: str, password: str) -> str:
        user = self._store.get_user_by_username(username)
        if not user:
            raise InvalidCredentialsError("Invalid username or password")

        password_hash = self._store.get_password_hash(username)
        if not verify_password(password, password_hash):
            raise InvalidCredentialsError("Invalid username or password")

        if not user.verified:
            raise UnverifiedUserError("User email not verified")

        session_token = generate_token()
        self._store.add_session(
            UserToken(
                username=username,
                token_hash=hash_token(session_token, self._secret_key),
                expires_at=utcnow() + self._session_token_ttl,
            )
        )
        return session_token

    def verify_session(self, session_token: str) -> bool:
        try:
            self._get_valid_session(session_token)
            return True
        except InvalidSessionTokenError:
            return False

    def get_current_user(self, session_token: str) -> UserT:
        session = self._get_valid_session(session_token)
        if user := self._store.get_user_by_username(session.username):
            return user
        raise InvalidSessionTokenError("Invalid session token")

    def logout(self, session_token: str) -> None:
        session = self._get_valid_session(session_token)
        self._store.remove_session(session.token_hash)

    def logout_all(self, session_token: str) -> None:
        session = self._get_valid_session(session_token)
        self._store.remove_all_sessions(session.username)

    def send_password_reset(self, email: str) -> None:
        user = self._store.get_user_by_email(email)
        if not user:
            return
        reset_token = generate_token()
        self._store.set_password_reset(
            UserToken(
                username=user.username,
                token_hash=hash_token(reset_token, self._secret_key),
                expires_at=utcnow() + self._password_reset_token_ttl,
            )
        )
        self._email_sender.send_password_reset(user.username, email, reset_token)

    def reset_password(self, new_password: str, reset_token: str) -> None:
        reset_token_hash = hash_token(reset_token, self._secret_key)
        new_password_hash = hash_password(new_password)
        with self._store.transaction():
            password_reset = self._store.get_password_reset(reset_token_hash)
            if not password_reset:
                raise InvalidPasswordResetTokenError("Invalid password reset token")
            if utcnow() > as_aware_utc(password_reset.expires_at):
                self._store.remove_password_reset(password_reset.token_hash)
                raise InvalidPasswordResetTokenError("Password reset token expired")
            if not is_password_strong(new_password):
                raise WeakPasswordError("Weak new password")
            self._store.set_password_hash(password_reset.username, new_password_hash)
            self._store.remove_all_sessions(password_reset.username)
            self._store.remove_password_reset(password_reset.token_hash)

    def change_password(
        self, old_password: str, new_password: str, session_token: str
    ) -> None:
        new_password_hash = hash_password(new_password)
        with self._store.transaction():
            session = self._get_valid_session(session_token)
            if not verify_password(
                old_password, self._store.get_password_hash(session.username)
            ):
                raise InvalidCredentialsError("Invalid old password")
            if not is_password_strong(new_password):
                raise WeakPasswordError("Weak new password")
            self._store.set_password_hash(session.username, new_password_hash)
            self._store.remove_all_sessions(session.username)

    def delete_account(self, password: str, session_token: str) -> None:
        with self._store.transaction():
            session = self._get_valid_session(session_token)
            if not verify_password(
                password, self._store.get_password_hash(session.username)
            ):
                raise InvalidCredentialsError("Invalid password")
            self._store.remove_all_sessions(session.username)
            self._store.delete_user(session.username)

    def _get_valid_session(self, session_token: str) -> UserToken:
        session = self._store.get_session(hash_token(session_token, self._secret_key))
        if not session:
            raise InvalidSessionTokenError("Invalid session token")
        now = utcnow()
        session_expires_at = as_aware_utc(session.expires_at)
        if session_expires_at < now:
            self._store.remove_session(session.token_hash)
            raise InvalidSessionTokenError("Session token expired")
        if (
            self._session_refresh_threshold
            and session_expires_at - now < self._session_refresh_threshold
        ):
            refreshed_expires_at = now + self._session_token_ttl
            self._store.refresh_session(session.token_hash, refreshed_expires_at)
            session.expires_at = refreshed_expires_at
        return session
