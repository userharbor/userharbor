from typing import Protocol


class Store(Protocol):
    def create_user(self, username: str, email: str, password: str) -> None: ...


class UserHarbor:
    def __init__(self, secret_key: str, store: Store):
        self._secret_key = secret_key
        self._store = store

    def register(self, username: str, email: str, password: str) -> None:
        self._store.create_user(username, email, password)
