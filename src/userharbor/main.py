from typing import Protocol

from .exceptions import InvalidEmailError, InvalidUsernameError, WeakPasswordError
from .password_utils import generate_verification_code
from .validations import is_email_valid, is_password_strong, is_username_valid


class UserStore(Protocol):
    def create_user(
        self, username: str, email: str, password_hash: str, verification_code_hash: str
    ) -> None: ...

    def verify_user(self, username: str, verification_code_hash: str) -> None: ...


class EmailSender(Protocol):
    def send_verification(
        self, username: str, email: str, verification_code: str
    ) -> None: ...


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

        verification_code = generate_verification_code()
        self._store.create_user(username, email, password, verification_code)
        self._email_sender.send_verification(username, email, verification_code)

    def verify(self, username: str, verification_code: str) -> None:
        self._store.verify_user(username, verification_code)
