from typing import Generic

from .interfaces import UserList, UserStore, UserT
from .normalizations import normalize_email


class UserManager(Generic[UserT]):
    def __init__(self, store: UserStore[UserT]) -> None:
        self._store = store

    def get_by_username(self, username: str) -> UserT | None:
        return self._store.get_user_by_username(username)

    def get_by_email(self, email: str) -> UserT | None:
        return self._store.get_user_by_email(normalize_email(email))

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order: str = "username",
        query: str | None = None,
    ) -> UserList[UserT]:
        if not 1 <= limit <= 500:
            raise ValueError("Limit must be between 1 and 500")
        if offset < 0:
            raise ValueError("Offset must not be negative")
        return self._store.list_users(
            limit=limit, offset=offset, order=order, query=query
        )
