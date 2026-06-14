from secrets import token_urlsafe
from typing import Protocol


class UserStore(Protocol):
    def create_user(
        self, username: str, email: str, password: str, verification_code: str
    ) -> None: ...

    def verify_user(self, username: str, verification_code: str) -> None: ...


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
        verification_code = _generate_verification_code()
        self._store.create_user(username, email, password, verification_code)
        self._email_sender.send_verification(username, email, verification_code)

    def verify(self, username: str, verification_code: str) -> None:
        self._store.verify_user(username, verification_code)


def _generate_verification_code() -> str:
    return token_urlsafe(16)
