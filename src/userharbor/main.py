from .exceptions import (
    InvalidEmailError,
    InvalidUsernameError,
    InvalidVerificationCodeError,
    WeakPasswordError,
)
from .interfaces import EmailSender, UserStore
from .security import (
    generate_token,
    hash_password,
    hash_token,
    verify_token,
)
from .validations import is_email_valid, is_password_strong, is_username_valid


class UserHarbor:
    def __init__(
        self, secret_key: str, store: UserStore, email_sender: EmailSender
    ) -> None:
        self._secret_key = secret_key
        self._store = store
        self._email_sender = email_sender

    def register(self, username: str, email: str, password: str) -> None:
        if not is_username_valid(username):
            raise InvalidUsernameError("Invalid username")
        if not is_email_valid(email):
            raise InvalidEmailError("Invalid email")
        if not is_password_strong(password):
            raise WeakPasswordError("Weak password")

        verification_code = generate_token()
        self._store.create_user(
            username,
            email,
            hash_password(password),
            hash_token(verification_code, self._secret_key),
        )
        self._email_sender.send_verification(username, email, verification_code)

    def verify(self, username: str, verification_code: str) -> None:
        verification_code_hash = self._store.get_email_verification_code_hash(username)
        if not verify_token(
            verification_code, verification_code_hash, self._secret_key
        ):
            raise InvalidVerificationCodeError("Invalid verification code")
        self._store.set_user_verified(username)

    #
    # def login(self, username: str, password: str) -> None:
    #     password_hash = self._store.get_password_hash(username)
    #     if not verify_password(password, password_hash):
    #         raise InvalidPasswordError("Invalid password")
