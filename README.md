<picture>
  <img src="https://github.com/userharbor/userharbor/raw/master/docs/assets/logo-full.png" alt="userharbor">
</picture>

<!-- --8<-- [start:intro] -->

[![GitHub License](https://img.shields.io/github/license/userharbor/userharbor)](https://github.com/userharbor/userharbor?tab=MIT-1-ov-file)
[![Tests](https://img.shields.io/github/actions/workflow/status/userharbor/userharbor/publish.yml?label=tests)](https://github.com/userharbor/userharbor/blob/master/.github/workflows/tests.yml)
[![Codecov](https://img.shields.io/codecov/c/github/userharbor/userharbor)](https://codecov.io/gh/userharbor/userharbor)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/userharbor)](https://pypi.org/project/userharbor)
[![PyPI - Version](https://img.shields.io/pypi/v/userharbor)](https://pypi.org/project/userharbor)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/badge/linting-Ruff-black?logo=ruff&logoColor=black)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Pytest](https://img.shields.io/badge/testing-Pytest-red?logo=pytest&logoColor=red)](https://docs.pytest.org/)
[![Zensical](https://img.shields.io/badge/docs-Zensical-yellow?logo=MaterialForMkDocs&logoColor=yellow)](https://userharbor.github.io/userharbor/)

> **Project status:** UserHarbor is currently in an early stage of development.
> The API may change frequently. The library is not ready for production use yet.

**UserHarbor** is a framework-agnostic Python library for user account management.

Its goal is to provide a simple, stable, and framework-independent interface for common user-related operations:

* user registration,
* email verification,
* login,
* session management,
* logout from one or all sessions,
* password change,
* password reset,
* account deletion.

UserHarbor is not a web framework. It does not provide routers, views, or HTTP endpoints.
Instead, it exposes a simple domain-level API that can be integrated with FastAPI, Flask, Django, Litestar, CLI applications, or any other environment.

## Installation

Install the core package if you want to provide your own `UserStore` and
`EmailSender` implementations:

```bash
pip install userharbor
```

Install the core package with the official SQLAlchemy and SMTP adapters:

```bash
pip install "userharbor[sqlalchemy,smtp]"
```

The official adapters are documented in the
[integrations documentation](https://userharbor.github.io/userharbor/integrations/):

* [`userharbor-sqlalchemy`](https://github.com/userharbor/userharbor-sqlalchemy)
* [`userharbor-smtp`](https://github.com/userharbor/userharbor-smtp)

## Quick example

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from userharbor import UserHarbor
from userharbor_sqlalchemy import SQLAlchemyUserStore
from userharbor_smtp import SMTPEmailSender

engine = create_engine("sqlite:///users.db")
SessionLocal = sessionmaker(bind=engine)

store = SQLAlchemyUserStore(SessionLocal)
store.metadata.create_all(engine)

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

# Logout
harbor.logout(session_token)

# Change password
session_token = harbor.login(
    username="jane",
    password="StrongPassword123!",
)
harbor.change_password(
    old_password="StrongPassword123!",
    new_password="EvenStrongerPassword123!",
    session_token=session_token,
)

# Send password reset email
harbor.send_password_reset("jane@example.com")

# Reset password
harbor.reset_password(
    new_password="NewStrongPassword123!",
    reset_token="reset-token-from-email",
)

# Delete account
session_token = harbor.login(
    username="jane",
    password="NewStrongPassword123!",
)
harbor.delete_account(
    password="NewStrongPassword123!",
    session_token=session_token,
)
```

<!-- --8<-- [end:intro] -->

## Documentation

The full documentation is available at
[userharbor.github.io/userharbor](https://userharbor.github.io/userharbor/).

Useful pages:

* [Architecture](https://userharbor.github.io/userharbor/architecture/)
* [Design principles](https://userharbor.github.io/userharbor/design-principles/)
* [Integrations](https://userharbor.github.io/userharbor/integrations/)
* [Contributing](https://userharbor.github.io/userharbor/Development/contributing/)

## Architecture

<!-- --8<-- [start:architecture] -->

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

The main `userharbor` package does not contain a concrete database
implementation or email delivery implementation.

Instead, it relies on two protocols:

* `UserStore`,
* `EmailSender`.

This allows you to use official adapters or build your own integration.

<!-- --8<-- [end:architecture] -->

## Official integrations

<!-- --8<-- [start:integrations] -->

UserHarbor core does not include database or email-provider implementations.
Those responsibilities are handled by adapters that implement the core
`UserStore` and `EmailSender` protocols.

Official integrations:

* [`userharbor-sqlalchemy`](https://github.com/userharbor/userharbor-sqlalchemy)
  provides a SQLAlchemy-based `UserStore`.
* [`userharbor-smtp`](https://github.com/userharbor/userharbor-smtp) provides an
  SMTP-based `EmailSender`.
* [`userharbor-fastapi`](https://github.com/userharbor/userharbor-fastapi) is in
  preparation.

See the [integrations documentation](https://userharbor.github.io/userharbor/integrations/)
for detailed setup instructions.

<!-- --8<-- [end:integrations] -->

## Design principles

<!-- --8<-- [start:design-principles] -->

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

Such features may be created as separate libraries or integrations, but they
should not complicate the core project.

UserHarbor should not become an application framework.

### 2. Framework-agnostic before framework integrations

The main library should not depend on FastAPI, Django, Flask, Litestar, or any
other framework.

Framework integrations should be created as separate libraries.

### 3. UserStore and EmailSender are dependencies

UserHarbor does not assume where users are stored.

UserHarbor does not assume how email messages are sent.

These responsibilities belong to adapters compatible with the `UserStore` and
`EmailSender` interfaces.

### 4. Adapters should live outside the core

Integrations with databases, ORMs, email services, queues, frameworks, and
providers should be developed as separate packages.

### 5. Stability is more important than feature count

After the public API becomes stable, further core development should focus
mainly on:

* improving security,
* improving reliability,
* improving performance,
* maintaining compatibility.

New features should be added carefully.

### 6. Simple things should remain simple

The library should be easy to use in small projects, while still being possible
to extend in larger applications.

<!-- --8<-- [end:design-principles] -->

## Changelog

<!-- --8<-- [start:changelog] -->

Changes for each release are documented in the
[GitHub release notes](https://github.com/userharbor/userharbor/releases).

<!-- --8<-- [end:changelog] -->

## Contributing

<!-- --8<-- [start:contributing] -->

The project is in an early stage of development and its API is not stable yet.

The most welcome areas of contribution are:

* public API design,
* security improvements,
* tests,
* documentation,
* `UserStore` implementations,
* `EmailSender` implementations,
* framework integrations as separate packages.

Before starting work on a storage or email integration, review the official
adapters:

```text
https://github.com/userharbor/userharbor-sqlalchemy
https://github.com/userharbor/userharbor-smtp
```

<!-- --8<-- [end:contributing] -->

## License

UserHarbor is released under the MIT License.
