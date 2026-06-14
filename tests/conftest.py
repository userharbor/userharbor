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
    session_token_hashes: list[str] | None = None

    def __post_init__(self) -> None:
        if self.session_token_hashes is None:
            self.session_token_hashes = []


@dataclass
class SentVerification:
    username: str
    email: str
    verification_code: str


@dataclass
class RegisteredUser:
    username: str
    email: str
    password: str
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
        session_token_hashes = self.users[username].session_token_hashes
        assert session_token_hashes is not None
        session_token_hashes.append(session_token_hash)

    def get_session_token_hash(self, username: str) -> str:
        session_token_hashes = self.users[username].session_token_hashes
        assert session_token_hashes is not None
        return session_token_hashes[-1]

    def remove_session(self, username: str, session_token_hash: str) -> None:
        session_token_hashes = self.users[username].session_token_hashes
        assert session_token_hashes is not None
        session_token_hashes.remove(session_token_hash)

    def remove_all_sessions(self, username: str) -> None:
        session_token_hashes = self.users[username].session_token_hashes
        assert session_token_hashes is not None
        session_token_hashes.clear()


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


@pytest.fixture
def register_user(userharbor: UserHarbor, email_sender: RecordingEmailSender):
    def _register_user(
        username: str = VALID_USERNAME,
        email: str = VALID_EMAIL,
        password: str = VALID_PASSWORD,
    ) -> RegisteredUser:
        userharbor.register(username, email, password)
        return RegisteredUser(
            username=username,
            email=email,
            password=password,
            verification_code=email_sender.sent_verifications[-1].verification_code,
        )

    return _register_user


@pytest.fixture
def verified_user(userharbor: UserHarbor, register_user):
    registered_user = register_user()
    userharbor.verify_email(registered_user.username, registered_user.verification_code)
    return registered_user


@pytest.fixture
def logged_in_user(userharbor: UserHarbor, verified_user: RegisteredUser):
    session_token = userharbor.login(verified_user.username, verified_user.password)
    return verified_user, session_token
