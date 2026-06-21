---
title: Custom Integrations
description: How to build storage, email, framework, or provider integrations for UserHarbor.
icon: lucide/puzzle

---
# Custom Integrations

UserHarbor integrations should live outside the core package. The core library
owns account-management rules, token generation, token hashing, and password
hashing. Integrations provide infrastructure-specific behavior behind small
protocols.

Common integration types include:

* database or ORM-backed `UserStore` implementations,
* email-provider `EmailSender` implementations,
* framework packages that wire UserHarbor into routes, dependencies, or request
  handling,
* provider adapters for services such as SendGrid, Resend, Mailgun, Redis, or
  MongoDB.

Before creating a new adapter, review the official implementations:

```text
https://github.com/userharbor/userharbor-sqlalchemy
https://github.com/userharbor/userharbor-smtp
```

## Package structure

Keep custom integrations as separate packages. A typical package can be small:

```text
userharbor-myadapter/
    pyproject.toml
    README.md
    src/
        userharbor_myadapter/
            __init__.py
            py.typed
            store.py
            sender.py
    tests/
```

Only include the files your adapter needs. A storage adapter does not need an
email sender, and an email adapter does not need database code.

## UserStore integrations

Implement `UserStore` when your adapter is responsible for persistence.

```python
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass

from userharbor.interfaces import CreateUserRequest, UserStore, UserToken


@dataclass
class MyUser:
    username: str
    email: str
    verified: bool


class MyUserStore(UserStore[MyUser]):
    def transaction(self) -> AbstractContextManager[None]:
        return nullcontext()

    def create_user(self, user: CreateUserRequest) -> None:
        ...

    def set_user_verified(self, username: str) -> None:
        ...

    def delete_user(self, username: str) -> None:
        ...

    def get_user_by_username(self, username: str) -> MyUser | None:
        ...

    def get_user_by_email(self, email: str) -> MyUser | None:
        ...

    def get_email_verification(self, token_hash: str) -> UserToken | None:
        ...

    def set_email_verification(self, verification: UserToken) -> None:
        ...

    def remove_email_verification(self, token_hash: str) -> None:
        ...

    def get_session(self, token_hash: str) -> UserToken | None:
        ...

    def add_session(self, session: UserToken) -> None:
        ...

    def remove_session(self, token_hash: str) -> None:
        ...

    def remove_all_sessions(self, username: str) -> None:
        ...

    def get_password_hash(self, username: str) -> str:
        ...

    def set_password_hash(self, username: str, password_hash: str) -> None:
        ...

    def get_password_reset(self, token_hash: str) -> UserToken | None:
        ...

    def set_password_reset(self, reset: UserToken) -> None:
        ...

    def remove_password_reset(self, token_hash: str) -> None:
        ...
```

A `UserStore` is responsible for:

* creating and deleting users,
* storing password hashes,
* storing email verification token hashes,
* storing session token hashes,
* storing password reset token hashes,
* removing sessions and tokens,
* providing transaction boundaries for multi-step updates.

The store should never store raw tokens. UserHarbor passes token hashes to the
store and keeps raw token handling in the core flow.

The user type returned by `get_user_by_username()` and `get_user_by_email()` can
be any object that provides `username`, `email`, and `verified`. Parameterize
`UserStore` with that concrete type so `UserHarbor.get_current_user()` preserves
it in type checkers.

## Transactions

`transaction()` should return a context manager. UserHarbor uses it around
operations that update multiple related records, such as email verification,
password reset, password change, and account deletion.

For stores that support transactions, commit when the block finishes
successfully and roll back when an exception is raised.

For simple in-memory or non-transactional adapters, `nullcontext()` can be enough
while prototyping, but production stores should provide real consistency when
the backend supports it.

## EmailSender integrations

Implement `EmailSender` when your adapter is responsible for message delivery.

```python
from userharbor.interfaces import EmailSender


class MyEmailSender(EmailSender):
    def send_verification(
        self,
        username: str,
        email: str,
        verification_token: str,
    ) -> None:
        ...

    def send_password_reset(
        self,
        username: str,
        email: str,
        reset_token: str,
    ) -> None:
        ...
```

An `EmailSender` should only send messages. It should not decide whether a token
is valid, hash tokens, verify users, or reset passwords. Those responsibilities
belong to UserHarbor core.

## Framework integrations

Framework integrations should compose UserHarbor with framework-specific tools
instead of moving domain behavior into the framework package.

A framework adapter may provide:

* dependency helpers,
* route or router factories,
* request-to-command mapping,
* response models,
* examples for configuring stores and email senders.

It should avoid hard-coding one database or email provider unless that is the
explicit purpose of the package. Prefer accepting a configured `UserHarbor`
instance or accepting `UserStore` and `EmailSender` implementations from the
application.

## Testing checklist

Custom integrations should include tests for the contract they implement.

For `UserStore`, cover:

* user creation and lookup by username and email,
* email verification token storage and removal,
* session creation, lookup, removal, and remove-all behavior,
* password hash lookup and update,
* password reset token storage and removal,
* transaction commit and rollback behavior.

For `EmailSender`, cover:

* verification messages,
* password reset messages,
* subject and sender configuration,
* template rendering, if templates are supported,
* provider authentication or API calls using fakes.

## Public API

Export the main adapter class from the package root:

```python
from .store import MyUserStore

__all__ = ["MyUserStore"]
```

If the package is typed, include `py.typed` and configure packaging so it is
included in distributions.

## Naming

Use a clear package name that identifies the target integration:

```text
userharbor-sqlalchemy
userharbor-smtp
userharbor-fastapi
userharbor-sendgrid
userharbor-redis
```

Keep the adapter focused. If one package starts combining unrelated storage,
email, and framework behavior, split it into smaller packages.
