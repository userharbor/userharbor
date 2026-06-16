from datetime import datetime, timedelta

from .exceptions import (
    InvalidEmailError,
    InvalidPasswordError,
    InvalidSessionTokenError,
    InvalidUsernameError,
    InvalidVerificationTokenError,
    UnverifiedUserError,
    WeakPasswordError,
)
from .interfaces import CreateUserRequest, EmailSender, UserStore
from .security import (
    generate_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token,
)
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

        verification_code = generate_token()
        self._store.create_user(
            CreateUserRequest(
                username=username,
                email=email,
                password=hash_password(password),
                verification_code_hash=hash_token(verification_code, self._secret_key),
                expires_at=datetime.now() + timedelta(hours=24),
            )
        )
        self._email_sender.send_verification(username, email, verification_code)

    def verify_email(self, verification_code: str) -> None:
        verification = self._store.get_email_verification(
            hash_token(verification_code, self._secret_key)
        )
        if not verification:
            raise InvalidVerificationTokenError("Invalid verification token")
        if datetime.now() > verification.expires_at:
            self._store.remove_email_verification(verification.verification_code_hash)
            raise InvalidVerificationTokenError("Verification token expired")
        self._store.remove_email_verification(verification.verification_code_hash)
        self._store.set_user_verified(verification.username)

    def verify_session(self, session_token: str) -> bool:
        session = self._store.get_session(hash_token(session_token, self._secret_key))
        if not session:
            return False
        if datetime.now() > session.expires_at:
            self._store.remove_session(session.token_hash)
            return False
        return True

    def login(self, username: str, password: str) -> str:
        password_hash = self._store.get_password_hash(username)
        if not verify_password(password, password_hash):
            raise InvalidPasswordError("Invalid password")
        if not self._store.is_user_verified(username):
            raise UnverifiedUserError("User email not verified")
        session_token = generate_token()
        self._store.add_session(username, hash_token(session_token, self._secret_key))
        return session_token

    def logout(self, session_token: str) -> None:
        if not self.verify_session(session_token):
            raise InvalidSessionTokenError("Invalid session token")
        self._store.remove_session(hash_token(session_token, self._secret_key))

    def logout_all(self, username: str, session_token: str) -> None:
        if not self.verify_session(session_token):
            raise InvalidSessionTokenError("Invalid session token")
        self._store.remove_all_sessions(username)

    def change_password(
        self, username: str, old_password: str, new_password: str, session_token: str
    ) -> None:
        if not self.verify_session(session_token):
            raise InvalidSessionTokenError("Invalid session token")
        if not verify_password(old_password, self._store.get_password_hash(username)):
            raise InvalidPasswordError("Invalid old password")
        if not is_password_strong(new_password):
            raise WeakPasswordError("Weak new password")
        self._store.set_password_hash(username, hash_password(new_password))

    def send_password_reset(self, username: str, email: str) -> None:
        if not self._store.is_user_exists(username, email):
            raise InvalidUsernameError("Invalid username or email")
        reset_token = generate_token()
        self._store.set_password_reset_token_hash(
            username, hash_token(reset_token, self._secret_key)
        )
        self._email_sender.send_password_reset(username, email, reset_token)

    def reset_password(
        self, username: str, new_password: str, reset_token: str
    ) -> None:
        reset_token_hash = self._store.get_password_reset_token_hash(username)
        if not verify_token(reset_token, reset_token_hash, self._secret_key):
            raise InvalidVerificationTokenError("Invalid password reset token")
        if not is_password_strong(new_password):
            raise WeakPasswordError("Weak new password")
        self._store.set_password_hash(username, hash_password(new_password))

    def delete_account(self, username: str, password: str, session_token: str) -> None:
        if not self.verify_session(session_token):
            raise InvalidSessionTokenError("Invalid session token")
        if not verify_password(password, self._store.get_password_hash(username)):
            raise InvalidPasswordError("Invalid password")
        self._store.remove_all_sessions(username)
        self._store.delete_user(username)
