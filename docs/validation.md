---
title: Validation
description: Configure username and password validation in UserHarbor.
icon: lucide/list-checks

---
# Validation

UserHarbor validates usernames during registration and passwords during
registration, password changes, and password resets. It provides default
validators and allows each `UserHarbor` instance to replace them with
application-specific functions.

Validators receive a string and return `True` when the value is valid or
`False` when it should be rejected.

## Email normalization

UserHarbor converts email addresses to lowercase before storing or looking them
up. The normalized address is also used when sending verification and password
reset emails. For example, `Jane@Example.COM` is stored as
`jane@example.com`.

UserHarbor does not remove dots, `+tag` suffixes, or whitespace. Those
transformations are provider-specific or can change the address meaning.

## Default username validation

The default username validator requires a username to:

* contain between 3 and 32 characters
* contain only letters, numbers, and underscores

The 32-character maximum keeps usernames readable while leaving enough room for
most human-readable and generated identifiers. Applications that need longer
usernames can provide a custom validator.

It accepts usernames such as:

```text
jane
jane123
jane_doe
```

Characters such as hyphens and spaces are rejected by default. Username
validation runs when a user registers. Operations involving an existing user
check whether that user exists without validating the username again.

Username casing is preserved, but username identity is compared using Unicode
`casefold()`. A user registered as `Jane_Doe` can log in as `jane_doe` or
`JANE_DOE`, while the stored and returned username remains `Jane_Doe`. A second
account cannot use a username with the same case-folded value.

An invalid username raises `InvalidUsernameError`.

## Default password validation

The default password validator requires a password to:

* contain at least 8 characters
* contain at least one lowercase letter
* contain at least one uppercase letter
* contain at least one number
* contain at least one non-alphanumeric character

Password validation runs during registration, password changes, and password
resets. A password that does not satisfy the configured validator raises
`WeakPasswordError`.

## Custom validators

Pass custom validators to `UserHarbor` as `username_validator` and
`password_validator`. A custom validator replaces the corresponding default
validator.

For short rules, validators can be defined with lambdas:

```python
from userharbor import UserHarbor


harbor = UserHarbor(
    secret_key="your-secret-key",
    store=store,
    email_sender=email_sender,
    username_validator=lambda username: len(username) >= 5,
    password_validator=lambda password: len(password) >= 16,
)
```

The username validator above accepts any username with at least 5 characters.
The password validator accepts any password with at least 16 characters. The
other requirements from the default validators no longer apply.

Use regular functions when validation rules need more detail:

```python
from userharbor import UserHarbor


RESERVED_USERNAMES = {"admin", "support", "system"}


def validate_username(username: str) -> bool:
    username_without_underscores = username.replace("_", "")
    return (
        3 <= len(username) <= 32
        and username_without_underscores.isalnum()
        and username.casefold() not in RESERVED_USERNAMES
    )


def validate_password(password: str) -> bool:
    return (
        len(password) >= 12
        and any(character.isalpha() for character in password)
        and any(character.isdigit() for character in password)
    )


harbor = UserHarbor(
    secret_key="your-secret-key",
    store=store,
    email_sender=email_sender,
    username_validator=validate_username,
    password_validator=validate_password,
)
```

Custom validators should be synchronous and should not modify application
state. If a validator raises an exception, UserHarbor stops the operation and
lets that exception propagate.
