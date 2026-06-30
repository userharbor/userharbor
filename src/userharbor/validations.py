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


def is_role_valid(role: str) -> bool:
    role_regex = r"^[a-z][a-z0-9_-]{1,63}$"
    return re.match(role_regex, role) is not None


def is_permission_valid(permission: str) -> bool:
    permission_regex = r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$"
    return re.match(permission_regex, permission) is not None
