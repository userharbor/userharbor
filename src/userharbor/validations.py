import re


def is_email_valid(email: str) -> bool:
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email) is not None


def is_username_valid(username: str) -> bool:
    return len(username) >= 3 and username.isalnum()


def is_password_strong(password: str) -> bool:
    if len(password) < 8:
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char.isupper() for char in password):
        return False
    if all((char.isalnum() for char in password)):
        return False
    return any((char.islower() for char in password))
