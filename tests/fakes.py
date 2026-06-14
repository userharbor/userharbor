from dataclasses import dataclass


@dataclass
class StoredUser:
    username: str
    email: str
    password_hash: str
    email_verification_code_hash: str
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
    verification_code: str


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

    def set_password_hash(self, username: str, password_hash: str) -> None:
        self.users[username].password_hash = password_hash

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

    def get_password_reset_token_hash(self, username: str) -> str:
        password_reset_token_hash = self.users[username].password_reset_token_hash
        assert password_reset_token_hash is not None
        return password_reset_token_hash

    def set_password_reset_token_hash(self, username: str, token_hash: str) -> None:
        self.users[username].password_reset_token_hash = token_hash

    def is_user_exists(self, username: str, email: str) -> bool:
        stored_user = self.users.get(username)
        return stored_user is not None and stored_user.email == email

    def delete_user(self, username: str) -> None:
        del self.users[username]


class RecordingEmailSender:
    def __init__(self) -> None:
        self.sent_verifications: list[SentVerification] = []
        self.sent_password_resets: list[SentPasswordReset] = []

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

    def send_password_reset(
        self, username: str, email: str, reset_code: str
    ) -> None:
        self.sent_password_resets.append(
            SentPasswordReset(
                username=username,
                email=email,
                reset_token=reset_code,
            )
        )
