from typing import Protocol

from .exceptions import (
    InvalidEmailError,
    InvalidUsernameError,
    InvalidVerificationCodeError,
    WeakPasswordError,
)
from .security import (
    generate_verification_code,
    hash_password,
    hash_verification_code,
    verify_verification_code,
)
from .validations import is_email_valid, is_password_strong, is_username_valid


class UserStore(Protocol):
    def create_user(
        self, username: str, email: str, password_hash: str, verification_code_hash: str
    ) -> None: ...
    def get_verification_code_hash(self, username: str) -> str: ...
    def set_user_verified(self, username: str) -> None: ...


class EmailSender(Protocol):
    def send_verification(
        self, username: str, email: str, verification_code: str
    ) -> None: ...


class UserHarbor:
    def __init__(self, store: UserStore, email_sender: EmailSender) -> None:
        self._store = store
        self._email_sender = email_sender

    def register(self, username: str, email: str, password: str) -> None:
        if not is_username_valid(username):
            raise InvalidUsernameError("Invalid username")
        if not is_email_valid(email):
            raise InvalidEmailError("Invalid email")
        if not is_password_strong(password):
            raise WeakPasswordError("Weak password")

        verification_code = generate_verification_code()
        self._store.create_user(
            username,
            email,
            hash_password(password),
            hash_verification_code(verification_code),
        )
        self._email_sender.send_verification(username, email, verification_code)

    def verify(self, username: str, verification_code: str) -> None:
        verification_code_hash = self._store.get_verification_code_hash(username)
        if not verify_verification_code(verification_code, verification_code_hash):
            raise InvalidVerificationCodeError("Invalid verification code")
        self._store.set_user_verified(username)
