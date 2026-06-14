from secrets import token_urlsafe

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def generate_verification_code() -> str:
    return token_urlsafe(16)


def hash_verification_code(verification_code: str) -> str:
    return password_hasher.hash(verification_code)


def verify_verification_code(
    verification_code: str, verification_code_hash: str
) -> bool:
    return password_hasher.verify(verification_code, verification_code_hash)
