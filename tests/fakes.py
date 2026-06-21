from contextlib import nullcontext
from dataclasses import dataclass

from userharbor.interfaces import (
    CreateUserRequest,
    EmailSender,
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

    def __post_init__(self) -> None:
        if self.session_token_hashes is None:
            self.session_token_hashes = []


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

    def transaction(self):
        return nullcontext()

    def create_user(self, user: CreateUserRequest) -> None:
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
        del self.email_verifications[token_hash]

    def set_user_verified(self, username: str) -> None:
        self.users[username].verified = True

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
        stored_user = self.users.get(username)
        if stored_user is None:
            return None
        return TestUser(
            username=stored_user.username,
            email=stored_user.email,
            verified=stored_user.verified,
        )

    def get_user_by_email(self, email: str) -> TestUser | None:
        for stored_user in self.users.values():
            if stored_user.email == email:
                return TestUser(
                    username=stored_user.username,
                    email=stored_user.email,
                    verified=stored_user.verified,
                )
        return None

    def remove_session(self, token_hash: str) -> None:
        session = self.sessions.pop(token_hash)
        session_token_hashes = self.users[session.username].session_token_hashes
        assert session_token_hashes is not None
        session_token_hashes.remove(token_hash)

    def remove_all_sessions(self, username: str) -> None:
        session_token_hashes = self.users[username].session_token_hashes
        assert session_token_hashes is not None
        for session_token_hash in session_token_hashes:
            del self.sessions[session_token_hash]
        session_token_hashes.clear()

    def get_password_reset(self, token_hash: str) -> UserToken | None:
        return self.password_resets.get(token_hash)

    def set_password_reset(self, reset: UserToken) -> None:
        old_token_hash = self.users[reset.username].password_reset_token_hash
        if old_token_hash is not None:
            self.password_resets.pop(old_token_hash, None)
        self.users[reset.username].password_reset_token_hash = reset.token_hash
        self.password_resets[reset.token_hash] = reset

    def remove_password_reset(self, token_hash: str) -> None:
        reset = self.password_resets.pop(token_hash)
        self.users[reset.username].password_reset_token_hash = None

    def delete_user(self, username: str) -> None:
        del self.users[username]


class RecordingEmailSender(EmailSender):
    def __init__(self) -> None:
        self.sent_verifications: list[SentVerification] = []
        self.sent_password_resets: list[SentPasswordReset] = []

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
