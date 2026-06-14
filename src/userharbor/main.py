from .exceptions import (
    InvalidEmailError,
    InvalidPasswordError,
    InvalidSessionTokenError,
    InvalidUsernameError,
    InvalidVerificationTokenError,
    UnverifiedUserError,
    WeakPasswordError,
)
from .interfaces import EmailSender, UserStore
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
            username,
            email,
            hash_password(password),
            hash_token(verification_code, self._secret_key),
        )
        self._email_sender.send_verification(username, email, verification_code)

    def verify_email(self, username: str, verification_code: str) -> None:
        verification_code_hash = self._store.get_email_verification_code_hash(username)
        if not verify_token(
            verification_code, verification_code_hash, self._secret_key
        ):
            raise InvalidVerificationTokenError("Invalid verification code")
        self._store.set_user_verified(username)

    def verify_session(self, username: str, session_token: str) -> bool:
        session_token_hash = self._store.get_session_token_hash(username)
        return verify_token(session_token, session_token_hash, self._secret_key)

    def login(self, username: str, password: str) -> str:
        password_hash = self._store.get_password_hash(username)
        if not verify_password(password, password_hash):
            raise InvalidPasswordError("Invalid password")
        if not self._store.is_user_verified(username):
            raise UnverifiedUserError("User email not verified")
        session_token = generate_token()
        self._store.add_session(username, hash_token(session_token, self._secret_key))
        return session_token

    def logout(self, username: str, session_token: str) -> None:
        if not self.verify_session(username, session_token):
            raise InvalidSessionTokenError("Invalid session token")
        self._store.remove_session(
            username, hash_token(session_token, self._secret_key)
        )

    def logout_all(self, username: str, session_token: str) -> None:
        if not self.verify_session(username, session_token):
            raise InvalidSessionTokenError("Invalid session token")
        self._store.remove_all_sessions(username)

    def change_password(
        self, username: str, old_password: str, new_password: str, session_token: str
    ) -> None:
        if not self.verify_session(username, session_token):
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
