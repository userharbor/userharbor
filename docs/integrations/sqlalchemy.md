---
title: SQLAlchemy Integration
description: Store UserHarbor users, sessions, tokens, roles, and permissions with SQLAlchemy.
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

* users
* password hashes
* email verification tokens
* sessions
* password reset tokens
* roles
* permissions
* user-to-role assignments
* role-to-permission assignments

It also updates session expiration when UserHarbor refreshes an active session.

It does not send emails, expose HTTP endpoints, or implement
application-specific authentication flows.

## Basic usage

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from userharbor_sqlalchemy import SQLAlchemyUserStore


engine = create_engine("sqlite:///users.db")
SessionLocal = sessionmaker(bind=engine)

store = SQLAlchemyUserStore(SessionLocal)
store.metadata.create_all(engine)
```

Pass `store` to `UserHarbor` as its `UserStore` implementation.

## Creating tables

The adapter exposes SQLAlchemy metadata through the store:

```python
store = SQLAlchemyUserStore(SessionLocal)

store.metadata.create_all(engine)
```

The built-in table names are:

* `userharbor_users`
* `userharbor_email_verifications`
* `userharbor_sessions`
* `userharbor_password_resets`
* `userharbor_roles`
* `userharbor_permissions`
* `userharbor_user_roles`
* `userharbor_role_permissions`

In applications that use migrations, include these models in your migration
metadata instead of calling `create_all()` at runtime.

## Custom user model

By default, the adapter creates and uses its own `userharbor_users` table. If
your application already owns a user table, pass that SQLAlchemy model as
`user_model`:

```python
from sqlalchemy import Boolean, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from userharbor_sqlalchemy import SQLAlchemyUserStore


class AppBase(DeclarativeBase):
    pass


class AppUser(AppBase):
    __tablename__ = "app_users"

    username: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    display_name: Mapped[str] = mapped_column(String(255), default="Anonymous")


engine = create_engine("sqlite:///users.db")
SessionLocal = sessionmaker(bind=engine)

store = SQLAlchemyUserStore(
    SessionLocal,
    user_model=AppUser,
)
store.metadata.create_all(engine)
```

Custom user models must provide:

* `username`
* `email`
* `password_hash`
* `verified`

The token and role assignment tables are still created by the adapter. Their
user foreign keys point to the table configured through `user_model`. When a
custom user model is provided, the adapter reuses that model's metadata, so
`store.metadata` contains both the application user model and the generated
UserHarbor token, role, permission, and assignment models.

## Custom user mapping

By default, SQLAlchemy user rows are mapped to a small public user object with
`username`, `email`, and `verified`. Pass `user_mapper` when your application
wants to return a richer public user type:

```python
from dataclasses import dataclass


@dataclass
class AppPublicUser:
    username: str
    email: str
    verified: bool
    display_name: str


store = SQLAlchemyUserStore(
    SessionLocal,
    user_model=AppUser,
    user_mapper=lambda user: AppPublicUser(
        username=user.username,
        email=user.email,
        verified=user.verified,
        display_name=user.display_name,
    ),
)
```

`user_mapper` is used by `get_user_by_username()` and `get_user_by_email()`.
Token methods continue to return `UserToken` values.

## Roles and permissions

`SQLAlchemyUserStore` implements the complete role and permission persistence
contract required by UserHarbor:

```python
harbor.roles.create("admin")
harbor.permissions.create("users.delete")
harbor.roles.grant_permission("admin", "users.delete")
harbor.grant_role("jane", "admin")
```

Roles and permissions are stored separately from users. User permissions are
derived through the `userharbor_user_roles` and `userharbor_role_permissions`
tables.

Deleting a role removes that role from users and removes its permission
assignments. Deleting a permission removes it from every role.

## Sessions and transactions

`SQLAlchemyUserStore` receives a session factory:

```python
store = SQLAlchemyUserStore(SessionLocal)
```

Each store method opens a session when no UserHarbor transaction is active.
`SQLAlchemyUserStore.transaction()` is used by UserHarbor for multi-step
operations such as email verification, password reset, password change, account
deletion, and other flows that need related writes to commit or roll back
together.

Role and permission methods use the same session handling as the account and
token methods.

Successful transaction blocks are committed. Exceptions roll back changes from
the block.

Session refreshes are persisted by the store when UserHarbor's sliding session
expiration is enabled.
