from typing import Generic

from .interfaces import UserStore, UserT


class UserManager(Generic[UserT]):
    def __init__(self, store: UserStore[UserT]) -> None:
        self._store = store

    def get_by_username(self, username: str) -> UserT | None:
        return self._store.get_user_by_username(username)
