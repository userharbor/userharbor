from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

from userharbor.interfaces import (
    CreateUserRequest,
    EmailSender,
    UserList,
    UserStore,
    UserToken,
)


@dataclass
class TestUser:
    username: str
    email: str
    verified: bool


@dataclass
class StoredUser:
    username: str
    email: str
    password_hash: str
    email_verification_token_hash: str
    verified: bool = False
    password_reset_token_hash: str | None = None
    session_token_hashes: list[str] | None = None
    roles: set[str] | None = None

    def __post_init__(self) -> None:
        if self.session_token_hashes is None:
            self.session_token_hashes = []
        if self.roles is None:
            self.roles = set()


@dataclass
class SentVerification:
    username: str
    email: str
    verification_token: str


@dataclass
class SentPasswordReset:
    username: str
    email: str
    reset_token: str


@dataclass
class SentAccountNotification:
    username: str
    email: str


@dataclass
class RegisteredUser:
    username: str
    email: str
    password: str
    verification_token: str


class InMemoryUserStore(UserStore[TestUser]):
    def __init__(self) -> None:
        self.users: dict[str, StoredUser] = {}
        self.email_verifications: dict[str, UserToken] = {}
        self.sessions: dict[str, UserToken] = {}
        self.password_resets: dict[str, UserToken] = {}
        self.roles: set[str] = set()
        self.permissions: set[str] = set()
        self.role_permissions: dict[str, set[str]] = {}
        self._transaction_depth = 0

    @contextmanager
    def transaction(self):
        snapshot = None
        if self._transaction_depth == 0:
            snapshot = deepcopy(
                (
                    self.users,
                    self.email_verifications,
                    self.sessions,
                    self.password_resets,
                    self.roles,
                    self.permissions,
                    self.role_permissions,
                )
            )
        self._transaction_depth += 1
        try:
            yield
        except Exception:
            if snapshot is not None:
                (
                    self.users,
                    self.email_verifications,
                    self.sessions,
                    self.password_resets,
                    self.roles,
                    self.permissions,
                    self.role_permissions,
                ) = snapshot
            raise
        finally:
            self._transaction_depth -= 1

    def create_user(self, user: CreateUserRequest) -> None:
        if any(
            username.casefold() == user.username.casefold()
            for username in self.users
        ) or any(
            stored_user.email == user.email for stored_user in self.users.values()
        ):
            raise ValueError("Username or email already exists")
        self.users[user.username] = StoredUser(
            username=user.username,
            email=user.email,
            password_hash=user.password_hash,
            email_verification_token_hash=user.verification_token_hash,
        )
        self.email_verifications[user.verification_token_hash] = UserToken(
            username=user.username,
            token_hash=user.verification_token_hash,
            expires_at=user.expires_at,
        )

    def get_email_verification(self, token_hash: str) -> UserToken | None:
        return self.email_verifications.get(token_hash)

    def set_email_verification(self, verification: UserToken) -> None:
        old_verification_token_hash = self.users[
            verification.username
        ].email_verification_token_hash
        self.email_verifications.pop(old_verification_token_hash, None)
        self.users[
            verification.username
        ].email_verification_token_hash = verification.token_hash
        self.email_verifications[verification.token_hash] = verification

    def remove_email_verification(self, token_hash: str) -> None:
        self.email_verifications.pop(token_hash, None)

    def set_user_verified(self, username: str) -> None:
        user = self.users.get(username)
        if user is not None:
            user.verified = True

    def get_password_hash(self, username: str) -> str:
        return self.users[username].password_hash

    def set_password_hash(self, username: str, password_hash: str) -> None:
        self.users[username].password_hash = password_hash

    def add_session(self, session: UserToken) -> None:
        session_token_hashes = self.users[session.username].session_token_hashes
        assert session_token_hashes is not None
        session_token_hashes.append(session.token_hash)
        self.sessions[session.token_hash] = session

    def get_session(self, token_hash: str) -> UserToken | None:
        return self.sessions.get(token_hash)

    def get_user_by_username(self, username: str) -> TestUser | None:
        username_key = username.casefold()
        for stored_user in self.users.values():
            if stored_user.username.casefold() == username_key:
                return TestUser(
                    username=stored_user.username,
                    email=stored_user.email,
                    verified=stored_user.verified,
                )
        return None

    def get_user_by_email(self, email: str) -> TestUser | None:
        for stored_user in self.users.values():
            if stored_user.email == email:
                return TestUser(
                    username=stored_user.username,
                    email=stored_user.email,
                    verified=stored_user.verified,
                )
        return None

    def list_users(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order: str = "username",
        query: str | None = None,
    ) -> UserList[TestUser]:
        query = (query or "").strip()
        users = [
            user
            for user in self.users.values()
            if query.casefold() in user.username.casefold()
            or query.lower() in user.email.lower()
        ]
        field = order.removeprefix("-")
        users.sort(key=lambda user: user.username.casefold())
        users.sort(
            key=lambda user: (
                user.username.casefold()
                if field == "username"
                else getattr(user, field)
            ),
            reverse=order.startswith("-"),
        )
        items = [
            TestUser(user.username, user.email, user.verified)
            for user in users[offset : offset + limit]
        ]
        return UserList(items=items, total=len(users))

    def remove_session(self, token_hash: str) -> None:
        session = self.sessions.pop(token_hash, None)
        if session is None:
            return
        session_token_hashes = self.users[session.username].session_token_hashes
        assert session_token_hashes is not None
        session_token_hashes.remove(token_hash)

    def remove_all_sessions(self, username: str) -> None:
        user = self.users.get(username)
        if user is None:
            return
        session_token_hashes = user.session_token_hashes
        assert session_token_hashes is not None
        for session_token_hash in session_token_hashes:
            del self.sessions[session_token_hash]
        session_token_hashes.clear()

    def refresh_session(self, token_hash: str, new_expires_at: datetime) -> None:
        session = self.sessions.get(token_hash)
        if session is not None:
            session.expires_at = new_expires_at

    def get_password_reset(self, token_hash: str) -> UserToken | None:
        return self.password_resets.get(token_hash)

    def set_password_reset(self, reset: UserToken) -> None:
        old_token_hash = self.users[reset.username].password_reset_token_hash
        if old_token_hash is not None:
            self.password_resets.pop(old_token_hash, None)
        self.users[reset.username].password_reset_token_hash = reset.token_hash
        self.password_resets[reset.token_hash] = reset

    def remove_password_reset(self, token_hash: str) -> None:
        reset = self.password_resets.pop(token_hash, None)
        if reset is not None:
            self.users[reset.username].password_reset_token_hash = None

    def remove_password_reset_for_user(self, username: str) -> None:
        user = self.users.get(username)
        if user is None or user.password_reset_token_hash is None:
            return
        self.password_resets.pop(user.password_reset_token_hash, None)
        user.password_reset_token_hash = None

    def delete_user(self, username: str) -> None:
        user = self.users.pop(username, None)
        if user is None:
            return
        self.email_verifications = {
            token_hash: token
            for token_hash, token in self.email_verifications.items()
            if token.username != username
        }
        self.sessions = {
            token_hash: token
            for token_hash, token in self.sessions.items()
            if token.username != username
        }
        self.password_resets = {
            token_hash: token
            for token_hash, token in self.password_resets.items()
            if token.username != username
        }

    def create_role(self, role: str) -> None:
        self.roles.add(role)
        self.role_permissions[role] = set()

    def delete_role(self, role: str) -> None:
        self.roles.discard(role)
        self.role_permissions.pop(role, None)
        for user in self.users.values():
            assert user.roles is not None
            user.roles.discard(role)

    def list_roles(self) -> set[str]:
        return self.roles.copy()

    def role_exists(self, role: str) -> bool:
        return role in self.roles

    def create_permission(self, permission: str) -> None:
        self.permissions.add(permission)

    def delete_permission(self, permission: str) -> None:
        self.permissions.discard(permission)
        for permissions in self.role_permissions.values():
            permissions.discard(permission)

    def list_permissions(self) -> set[str]:
        return self.permissions.copy()

    def permission_exists(self, permission: str) -> bool:
        return permission in self.permissions

    def grant_permission_to_role(self, role: str, permission: str) -> None:
        self.role_permissions[role].add(permission)

    def revoke_permission_from_role(self, role: str, permission: str) -> None:
        self.role_permissions[role].discard(permission)

    def get_role_permissions(self, role: str) -> set[str]:
        return self.role_permissions.get(role, set()).copy()

    def grant_role_to_user(self, username: str, role: str) -> None:
        roles = self.users[username].roles
        assert roles is not None
        roles.add(role)

    def revoke_role_from_user(self, username: str, role: str) -> None:
        roles = self.users[username].roles
        assert roles is not None
        roles.discard(role)

    def get_user_roles(self, username: str) -> set[str]:
        user = self.users.get(username)
        if user is None:
            return set()
        roles = user.roles
        assert roles is not None
        return roles.copy()

    def get_user_permissions(self, username: str) -> set[str]:
        permissions = set()
        user = self.users.get(username)
        if user is None:
            return permissions
        roles = user.roles
        assert roles is not None
        for role in roles:
            permissions.update(self.role_permissions[role])
        return permissions


class RecordingEmailSender(EmailSender):
    def __init__(self) -> None:
        self.sent_verifications: list[SentVerification] = []
        self.sent_password_resets: list[SentPasswordReset] = []
        self.sent_email_verified: list[SentAccountNotification] = []
        self.sent_password_changed: list[SentAccountNotification] = []
        self.sent_account_deleted: list[SentAccountNotification] = []

    def send_verification(
        self, username: str, email: str, verification_token: str
    ) -> None:
        self.sent_verifications.append(
            SentVerification(
                username=username,
                email=email,
                verification_token=verification_token,
            )
        )

    def send_password_reset(self, username: str, email: str, reset_token: str) -> None:
        self.sent_password_resets.append(
            SentPasswordReset(
                username=username,
                email=email,
                reset_token=reset_token,
            )
        )

    def send_email_verified(self, username: str, email: str) -> None:
        self.sent_email_verified.append(
            SentAccountNotification(
                username=username,
                email=email,
            )
        )

    def send_password_changed(self, username: str, email: str) -> None:
        self.sent_password_changed.append(
            SentAccountNotification(
                username=username,
                email=email,
            )
        )

    def send_account_deleted(self, username: str, email: str) -> None:
        self.sent_account_deleted.append(
            SentAccountNotification(
                username=username,
                email=email,
            )
        )
