from dataclasses import dataclass

import pytest

from userharbor.main import UserHarbor


VALID_USERNAME = "janek123"
VALID_EMAIL = "janek@example.com"
VALID_PASSWORD = "Strongpass1!"
SECRET_KEY = "test-secret-key"


@dataclass
class StoredUser:
    username: str
    email: str
    password_hash: str
    email_verification_code_hash: str
    verified: bool = False


@dataclass
class SentVerification:
    username: str
    email: str
    verification_code: str


class InMemoryUserStore:
    def __init__(self) -> None:
        self.users: dict[str, StoredUser] = {}

    def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        email_verification_code_hash: str,
    ) -> None:
        self.users[username] = StoredUser(
            username=username,
            email=email,
            password_hash=password_hash,
            email_verification_code_hash=email_verification_code_hash,
        )

    def get_email_verification_code_hash(self, username: str) -> str:
        return self.users[username].email_verification_code_hash

    def set_user_verified(self, username: str) -> None:
        self.users[username].verified = True

    def is_user_verified(self, username: str) -> bool:
        return self.users[username].verified

    def get_password_hash(self, username: str) -> str:
        return self.users[username].password_hash

    def add_session(self, username: str, session_token_hash: str) -> None:
        raise NotImplementedError

    def get_session_token_hash(self, username: str) -> str:
        raise NotImplementedError

    def remove_session(self, username: str, session_token_hash: str) -> None:
        raise NotImplementedError

    def remove_all_sessions(self, username: str) -> None:
        raise NotImplementedError


class RecordingEmailSender:
    def __init__(self) -> None:
        self.sent_verifications: list[SentVerification] = []

    def send_verification(
        self, username: str, email: str, verification_code: str
    ) -> None:
        self.sent_verifications.append(
            SentVerification(
                username=username,
                email=email,
                verification_code=verification_code,
            )
        )


@pytest.fixture
def store() -> InMemoryUserStore:
    return InMemoryUserStore()


@pytest.fixture
def email_sender() -> RecordingEmailSender:
    return RecordingEmailSender()


@pytest.fixture
def userharbor(
    store: InMemoryUserStore, email_sender: RecordingEmailSender
) -> UserHarbor:
    return UserHarbor(SECRET_KEY, store, email_sender)
