from secrets import token_urlsafe

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def generate_verification_code() -> str:
    return token_urlsafe(16)
