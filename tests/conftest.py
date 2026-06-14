from dataclasses import dataclass

import pytest

from userharbor.main import UserHarbor


VALID_USERNAME = "janek123"
VALID_EMAIL = "janek@example.com"
VALID_PASSWORD = "Strongpass1!"


@dataclass
class StoredUser:
    username: str
    email: str
    password_hash: str
    verification_code_hash: str
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
        self, username: str, email: str, password_hash: str, verification_code_hash: str
    ) -> None:
        self.users[username] = StoredUser(
            username=username,
            email=email,
            password_hash=password_hash,
            verification_code_hash=verification_code_hash,
        )

    def get_verification_code_hash(self, username: str) -> str:
        return self.users[username].verification_code_hash

    def set_user_verified(self, username: str) -> None:
        self.users[username].verified = True


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
    return UserHarbor(store, email_sender)
