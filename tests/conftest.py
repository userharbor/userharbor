import pytest
from fakes import InMemoryUserStore, RecordingEmailSender, RegisteredUser

from userharbor.main import UserHarbor

VALID_USERNAME = "janek123"
VALID_EMAIL = "janek@example.com"
VALID_PASSWORD = "Strongpass1!"
SECRET_KEY = "test-secret-key"


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
            verification_token=email_sender.sent_verifications[-1].verification_token,
        )

    return _register_user


@pytest.fixture
def verified_user(userharbor: UserHarbor, register_user):
    registered_user = register_user()
    userharbor.verify_email(registered_user.verification_token)
    return registered_user


@pytest.fixture
def logged_in_user(userharbor: UserHarbor, verified_user: RegisteredUser):
    session_token = userharbor.login(verified_user.username, verified_user.password)
    return verified_user, session_token
