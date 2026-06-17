from datetime import timedelta

from .exceptions import (
    InvalidEmailError,
    InvalidPasswordError,
    InvalidPasswordResetTokenError,
    InvalidSessionTokenError,
    InvalidUsernameError,
    InvalidVerificationTokenError,
    UnverifiedUserError,
    UserAlreadyVerifiedError,
    WeakPasswordError,
)
from .interfaces import CreateUserRequest, EmailSender, User, UserStore, UserToken
from .security import (
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from .utils import utcnow
from .validations import is_email_valid, is_password_strong, is_username_valid


class UserHarbor:
    def __init__(
        self, secret_key: str, store: UserStore, email_sender: EmailSender
    ) -> None:
        self._secret_key = secret_key
        self._store = store
        self._email_sender = email_sender

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
                expires_at=utcnow() + timedelta(hours=24),
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
            if utcnow() > verification.expires_at:
                self._store.remove_email_verification(verification.token_hash)
                raise InvalidVerificationTokenError("Verification token expired")
            self._store.remove_email_verification(verification.token_hash)
            self._store.set_user_verified(verification.username)

    def resend_verification(self, email: str) -> None:
        user = self._store.get_user_by_email(email)
        if not user:
            raise InvalidEmailError("Invalid email")
        if user.verified:
            raise UserAlreadyVerifiedError("User already verified")
        verification_token = generate_token()
        self._store.set_email_verification(
            UserToken(
                username=user.username,
                token_hash=hash_token(verification_token, self._secret_key),
                expires_at=utcnow() + timedelta(hours=24),
            )
        )
        self._email_sender.send_verification(user.username, email, verification_token)

    def login(self, username: str, password: str) -> str:
        user = self._store.get_user_by_username(username)
        if not user:
            raise InvalidPasswordError("Invalid username or password")

        password_hash = self._store.get_password_hash(username)
        if not verify_password(password, password_hash):
            raise InvalidPasswordError("Invalid password")

        if not user.verified:
            raise UnverifiedUserError("User email not verified")

        session_token = generate_token()
        self._store.add_session(
            UserToken(
                username=username,
                token_hash=hash_token(session_token, self._secret_key),
                expires_at=utcnow() + timedelta(days=30),
            )
        )
        return session_token

    def verify_session(self, session_token: str) -> bool:
        try:
            self._get_valid_session(session_token)
            return True
        except InvalidSessionTokenError:
            return False

    def get_current_user(self, session_token: str) -> User:
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
            raise InvalidEmailError("Invalid email")
        reset_token = generate_token()
        self._store.set_password_reset(
            UserToken(
                username=user.username,
                token_hash=hash_token(reset_token, self._secret_key),
                expires_at=utcnow() + timedelta(hours=1),
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
            if utcnow() > password_reset.expires_at:
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
                raise InvalidPasswordError("Invalid old password")
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
                raise InvalidPasswordError("Invalid password")
            self._store.remove_all_sessions(session.username)
            self._store.delete_user(session.username)

    def _get_valid_session(self, session_token: str) -> UserToken:
        session = self._store.get_session(hash_token(session_token, self._secret_key))
        if not session:
            raise InvalidSessionTokenError("Invalid session token")
        if utcnow() > session.expires_at:
            self._store.remove_session(session.token_hash)
            raise InvalidSessionTokenError("Session token expired")
        return session
