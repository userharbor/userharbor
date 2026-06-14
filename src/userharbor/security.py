import hmac
from hashlib import sha256
from secrets import token_urlsafe

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def generate_token() -> str:
    return token_urlsafe(16)


def hash_token(token: str, secret_key: str) -> str:
    return hmac.new(secret_key.encode(), token.encode(), sha256).hexdigest()


def verify_token(token: str, token_hash: str, secret_key: str) -> bool:
    return hmac.compare_digest(
        hash_token(token, secret_key),
        token_hash,
    )
