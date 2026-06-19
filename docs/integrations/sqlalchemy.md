---
title: SQLAlchemy Integration
description: Store UserHarbor users, sessions, and tokens with SQLAlchemy.
icon: lucide/database

---
# SQLAlchemy Integration

`userharbor-sqlalchemy` provides `SQLAlchemyUserStore`, a `UserStore`
implementation backed by SQLAlchemy 2.x.

Repository:

```text
https://github.com/userharbor/userharbor-sqlalchemy
```

## Installation

```bash
pip install userharbor-sqlalchemy
```

This package depends on `userharbor` and SQLAlchemy 2.x.

You can also install it through the core package extra:

```bash
pip install "userharbor[sqlalchemy]"
```

## What it stores

The adapter persists:

* users,
* password hashes,
* email verification tokens,
* sessions,
* password reset tokens.

It does not send emails, expose HTTP endpoints, or implement
application-specific authentication flows.

## Basic usage

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from userharbor import UserHarbor
from userharbor_sqlalchemy import SQLAlchemyUserStore
from userharbor_sqlalchemy.models import UserHarborBase


class EmailSender:
    def send_verification(
        self,
        username: str,
        email: str,
        verification_token: str,
    ) -> None:
        print(f"Send verification token to {email}: {verification_token}")

    def send_password_reset(
        self,
        username: str,
        email: str,
        reset_token: str,
    ) -> None:
        print(f"Send password reset token to {email}: {reset_token}")


engine = create_engine("sqlite:///users.db")
SessionLocal = sessionmaker(bind=engine)

UserHarborBase.metadata.create_all(engine)

store = SQLAlchemyUserStore(SessionLocal)

harbor = UserHarbor(
    secret_key="your-secret-key",
    store=store,
    email_sender=EmailSender(),
)

harbor.register(
    username="jane",
    email="jane@example.com",
    password="StrongPassword123!",
)

session_token = harbor.login(
    username="jane",
    password="StrongPassword123!",
)
```

For real applications, replace the example `EmailSender` with an implementation
that sends verification and password reset messages through your email provider.
The official [SMTP integration](smtp.md) can be used for that.

## Creating tables

The adapter exposes `UserHarborBase`, a SQLAlchemy declarative base containing
the UserHarbor tables:

```python
from userharbor_sqlalchemy.models import UserHarborBase

UserHarborBase.metadata.create_all(engine)
```

The built-in table names are:

* `userharbor_users`,
* `userharbor_email_verifications`,
* `userharbor_sessions`,
* `userharbor_password_resets`.

In applications that use migrations, include these models in your migration
metadata instead of calling `create_all()` at runtime.

## Sessions and transactions

`SQLAlchemyUserStore` receives a session factory:

```python
store = SQLAlchemyUserStore(SessionLocal)
```

Each store method opens a session when no UserHarbor transaction is active.
`SQLAlchemyUserStore.transaction()` is used by UserHarbor for multi-step
operations such as email verification, password reset, password change, and
account deletion.

Successful transaction blocks are committed. Exceptions roll back changes from
the block.

## Using with SMTP

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from userharbor import UserHarbor
from userharbor_sqlalchemy import SQLAlchemyUserStore
from userharbor_sqlalchemy.models import UserHarborBase
from userharbor_smtp import SMTPEmailSender

engine = create_engine("sqlite:///users.db")
SessionLocal = sessionmaker(bind=engine)
UserHarborBase.metadata.create_all(engine)

store = SQLAlchemyUserStore(SessionLocal)
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
```
