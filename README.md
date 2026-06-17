# UserHarbor

> **Project status:** UserHarbor is currently in an early stage of development.
> The API may change frequently. The library is not ready for production use yet.

**UserHarbor** is a framework-agnostic Python library for managing user accounts.

Its goal is to provide a simple, stable, and framework-independent interface for common user-related operations:

* user registration,
* email verification,
* login,
* session management,
* logout from one or all sessions,
* password change,
* forgotten password reset,
* account deletion.

UserHarbor is not a web framework. It does not provide routers, views, or HTTP endpoints.
Instead, it exposes a simple domain-level API that can be integrated with FastAPI, Flask, Django, Litestar, CLI applications, or any other environment.

---

## Installation

### Basic installation

If you want to use your own store and your own email delivery mechanism:

```bash
pip install userharbor
```

### Installation with default integrations

The default integrations are:

* [`userharbor-sqlalchemy`](https://github.com/userharbor/userharbor-sqlalchemy) — SQLAlchemy-based user store,
* [`userharbor-smtp`](https://github.com/userharbor/userharbor-smtp) — SMTP-based email sender.

```bash
pip install "userharbor[sqlalchemy,smtp]"
```

All official integrations can be found in the organization:

```text
https://github.com/userharbor
```

---

## Example usage

The example below shows UserHarbor with the default integrations: `SQLAlchemyUserStore` and `SMTPEmailSender`.

```python
from userharbor import UserHarbor
from userharbor_sqlalchemy import SQLAlchemyUserStore
from userharbor_smtp import SMTPEmailSender

store = SQLAlchemyUserStore.from_url("sqlite:///users.db")

email_sender = SMTPEmailSender(
    host="smtp.example.com",
    port=587,
    username="smtp-user",
    password="smtp-password",
    from_email="noreply@example.com",
)

harbor = UserHarbor(
    secret_key="your-secret-key",
    store=store,
    email_sender=email_sender,
)

# Register a user
harbor.register(
    username="jane",
    email="jane@example.com",
    password="StrongPassword123!",
)

# Verify email address
harbor.verify_email("verification-token-from-email")

# Login
session_token = harbor.login(
    username="jane",
    password="StrongPassword123!",
)

# Verify session
if harbor.verify_session(session_token):
    print("User is logged in")

# Get current user
current_user = harbor.get_current_user(session_token)
print(current_user.username)

# Change password
harbor.change_password(
    old_password="StrongPassword123!",
    new_password="EvenStrongerPassword123!",
    session_token=session_token,
)

# Delete account instead of logging out
harbor.delete_account(
    password="EvenStrongerPassword123!",
    session_token=session_token,
)

# Logout
harbor.logout(session_token)

# Send password reset email
harbor.send_password_reset(
    username="jane",
    email="jane@example.com",
)

# Reset password
harbor.reset_password(
    new_password="NewStrongPassword123!",
    reset_token="reset-token-from-email",
)
```

---

## Architecture

UserHarbor consists of three main parts:

```text
UserHarbor core
    ├── registration logic
    ├── login logic
    ├── session logic
    ├── password reset logic
    ├── data validation
    ├── token generation
    └── password and token hashing

UserStore
    └── any implementation responsible for storing users, sessions, and tokens

EmailSender
    └── any implementation responsible for sending email messages
```

The main `userharbor` package does not contain a concrete database implementation or email delivery implementation.

Instead, it relies on two protocols:

* `UserStore`,
* `EmailSender`.

This allows you to use official adapters or build your own integration.

---

## Official integrations

### SQLAlchemy

Repository:

```text
https://github.com/userharbor/userharbor-sqlalchemy
```

Package:

```bash
pip install userharbor-sqlalchemy
```

The SQLAlchemy integration provides an implementation of `UserStore`.

### SMTP

Repository:

```text
https://github.com/userharbor/userharbor-smtp
```

Package:

```bash
pip install userharbor-smtp
```

The SMTP integration provides an implementation of `EmailSender`.

---

## Project creed

UserHarbor should remain simple, predictable, and easy to integrate.

### 1. Core should only do what is necessary

The main library is responsible for basic user account operations:

* registration,
* email verification,
* login,
* session management,
* logout,
* password reset,
* password change,
* user deletion.

Unusual business-specific cases should be implemented outside the library.

UserHarbor should not become an application framework.

### 2. Framework-agnostic before framework integrations

The main library should not depend on FastAPI, Django, Flask, Litestar, or any other framework.

Framework integrations should be created as separate libraries.

### 3. UserStore and EmailSender are dependencies

UserHarbor does not assume where users are stored.

UserHarbor does not assume how email messages are sent.

These responsibilities belong to adapters compatible with the `UserStore` and `EmailSender` interfaces.

### 4. Adapters should live outside the core

Integrations with databases, ORMs, email services, queues, frameworks, and providers should be developed as separate packages.

Examples:

```text
userharbor-sqlalchemy
userharbor-smtp
userharbor-sendgrid
userharbor-resend
userharbor-fastapi
```

### 5. Stability is more important than feature count

After the public API becomes stable, further core development should focus mainly on:

* improving security,
* improving reliability,
* improving performance,
* maintaining compatibility.

New features should be added carefully.

### 6. Simple things should remain simple

The library should be easy to use in small projects, while still being possible to extend in larger applications.

---

## Creating custom integrations

UserHarbor encourages custom integrations to be created as separate libraries.

Possible examples:

* `userharbor-django`,
* `userharbor-redis`,
* `userharbor-mongodb`,
* `userharbor-sendgrid`,
* `userharbor-resend`,
* `userharbor-mailgun`,
* `userharbor-fastapi`.

If you want to create your own user storage adapter, start by reviewing:

```text
https://github.com/userharbor/userharbor-sqlalchemy
```

If you want to create your own email delivery adapter, start with:

```text
https://github.com/userharbor/userharbor-smtp
```

Integrations should implement the protocols shown below.

---

## `UserStore` interface

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class UserToken:
    username: str
    token_hash: str
    expires_at: datetime


@dataclass
class CreateUserRequest:
    username: str
    email: str
    password_hash: str
    verification_token_hash: str
    expires_at: datetime


@dataclass
class User:
    username: str
    email: str
    verified: bool


class UserStore(Protocol):
    def create_user(self, user: CreateUserRequest) -> None: ...
    def set_user_verified(self, username: str) -> None: ...
    def delete_user(self, username: str) -> None: ...
    def get_user_by_username(self, username: str) -> User | None: ...
    def get_user_by_email(self, email: str) -> User | None: ...

    def get_email_verification(self, token_hash: str) -> UserToken | None: ...
    def set_email_verification(self, verification: UserToken) -> None: ...
    def remove_email_verification(self, token_hash: str) -> None: ...

    def get_session(self, token_hash: str) -> UserToken | None: ...
    def add_session(self, session: UserToken) -> None: ...
    def remove_session(self, token_hash: str) -> None: ...
    def remove_all_sessions(self, username: str) -> None: ...

    def get_password_hash(self, username: str) -> str: ...
    def set_password_hash(self, username: str, password_hash: str) -> None: ...
    def get_password_reset(self, token_hash: str) -> UserToken | None: ...
    def set_password_reset(self, reset: UserToken) -> None: ...
    def remove_password_reset(self, token_hash: str) -> None: ...
```

A `UserStore` implementation is responsible for:

* creating users,
* storing password hashes,
* storing sessions,
* storing email verification tokens,
* storing password reset tokens,
* removing sessions and tokens,
* persisting data.

The store should not store raw tokens.

---

## `EmailSender` interface

```python
from typing import Protocol


class EmailSender(Protocol):
    def send_verification(
        self, username: str, email: str, verification_token: str
    ) -> None: ...

    def send_password_reset(
        self, username: str, email: str, reset_token: str
    ) -> None: ...
```

An `EmailSender` implementation is responsible only for sending messages.

It should not decide about:

* token validity,
* token hashing,
* registration logic,
* password reset logic,
* user verification logic.

These responsibilities belong to UserHarbor core.

---

## Project scope

UserHarbor does not try to solve every identity-related problem.

The following are outside the scope of the core library:

* OAuth,
* OpenID Connect,
* social login,
* 2FA/MFA,
* roles and permissions,
* ACL,
* organizations and teams,
* admin panels,
* ready-made HTTP endpoints,
* ready-made HTML views,
* integrations with specific frameworks.

Such features may be created as separate libraries or integrations, but they should not complicate the core project.

---

## Contributing

The project is in an early stage of development and its API is not stable yet.

The most welcome areas of contribution are:

* public API design,
* security improvements,
* tests,
* documentation,
* `UserStore` implementations,
* `EmailSender` implementations,
* framework integrations as separate packages.

Before starting work on a custom integration, consider reviewing the official adapters:

```text
https://github.com/userharbor/userharbor-sqlalchemy
https://github.com/userharbor/userharbor-smtp
```

---

## License

UserHarbor is released under the MIT License.
