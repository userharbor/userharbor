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

* database or ORM-backed `UserStore` implementations
* email-provider `EmailSender` implementations
* framework packages that wire UserHarbor into routes, dependencies, or request
  handling
* provider adapters for services such as SendGrid, Resend, Mailgun, Redis, or
  MongoDB

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

`UserStore` is one required contract, but it is composed from smaller protocols
for readability:

* `UserAccountStore`
* `TokenStore`
* `RoleStore`
* `PermissionStore`

Adapter packages should still pass one store object to `UserHarbor`.

```python
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime

from userharbor.interfaces import CreateUserRequest, UserList, UserStore, UserToken


@dataclass
class MyUser:
    username: str
    email: str
    verified: bool


class MyUserStore(UserStore[MyUser]):
    def transaction(self) -> AbstractContextManager[None]:
        ...

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

    def list_users(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order: str = "username",
        query: str | None = None,
    ) -> UserList[MyUser]:
        ...

    def get_password_hash(self, username: str) -> str:
        ...

    def set_password_hash(self, username: str, password_hash: str) -> None:
        ...

    # TokenStore

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

    def refresh_session(self, token_hash: str, new_expires_at: datetime) -> None:
        ...

    def get_password_reset(self, token_hash: str) -> UserToken | None:
        ...

    def set_password_reset(self, reset: UserToken) -> None:
        ...

    def remove_password_reset(self, token_hash: str) -> None:
        ...

    def remove_password_reset_for_user(self, username: str) -> None:
        ...

    # RoleStore

    def create_role(self, role: str) -> None:
        ...

    def delete_role(self, role: str) -> None:
        ...

    def list_roles(self) -> set[str]:
        ...

    def role_exists(self, role: str) -> bool:
        ...

    def grant_role_to_user(self, username: str, role: str) -> None:
        ...

    def revoke_role_from_user(self, username: str, role: str) -> None:
        ...

    def get_user_roles(self, username: str) -> set[str]:
        ...

    # PermissionStore

    def create_permission(self, permission: str) -> None:
        ...

    def delete_permission(self, permission: str) -> None:
        ...

    def list_permissions(self) -> set[str]:
        ...

    def permission_exists(self, permission: str) -> bool:
        ...

    def grant_permission_to_role(self, role: str, permission: str) -> None:
        ...

    def revoke_permission_from_role(self, role: str, permission: str) -> None:
        ...

    def get_role_permissions(self, role: str) -> set[str]:
        ...

    def get_user_permissions(self, username: str) -> set[str]:
        ...
```

A `UserStore` is responsible for:

* creating and deleting users
* storing password hashes
* storing email verification token hashes
* storing session token hashes
* storing password reset token hashes
* storing role and permission definitions
* storing role-to-permission assignments
* storing user-to-role assignments
* removing sessions and tokens
* updating session expiration when sliding session refresh is enabled
* providing transaction boundaries for multi-step updates

The store should never store raw tokens. UserHarbor passes token hashes to the
store and keeps raw token handling in the core flow.

User lookups and list items can return any public user type that provides
`username`, `email`, and `verified`. Parameterize `UserStore` with that concrete
type so `UserHarbor.get_current_user()` and `harbor.users` preserve it in type
checkers. See [User Manager](../user-manager.md) for usage examples.

### Contract semantics

A conforming `UserStore` must preserve the behavior expected by UserHarbor, not
only provide methods with matching signatures. In particular:

* usernames are unique using Unicode `casefold()` comparison while preserving
  the original casing
* `get_user_by_username()` compares usernames using Unicode `casefold()` and
  returns the stored user with their original username casing
* email addresses are unique; UserHarbor normalizes them to lowercase before
  passing them to the store
* creating a user and their initial email verification token is atomic
* a newly created user is not verified
* setting a new email verification token removes the user's previous
  verification token
* setting a new password reset token removes the user's previous reset token
* changing a user's password removes their active password reset token
* deleting a user removes their verification tokens, password reset tokens,
  sessions, and role assignments; reusing the username must not restore the
  previous account's roles or permissions
* deleting a missing user, token, session, role, or permission is a no-op
* refreshing a missing session and marking a missing user as verified are no-ops
* reading a missing user or token returns `None`
* `list_users()` returns a `UserList` with public user `items` and a `total`
  counting all matches before pagination, including when the requested page is empty
* listing searches username or email for the literal query substring without
  case sensitivity; whitespace around the query is ignored, and an empty query
  lists all users
* listing sorts by the named storage field, with an optional `-` prefix for
  descending order; username ordering uses `casefold()`, and equal sort values
  are ordered by the casefolded username ascending
* listing applies ordering and filtering before `offset` and `limit`; unknown
  order fields raise an error rather than falling back to a default
* reading roles or effective permissions for a missing user returns an empty set
* reading or updating a password hash for a missing user raises `KeyError`
* granting or revoking the same relationship more than once is idempotent
* deleting roles and permissions removes their relationship assignments

The shared contract tests are the executable specification for these rules.
Backend-specific exception types and persistence details remain the adapter's
responsibility.

### Transactions

`transaction()` should return a context manager. UserHarbor uses it around
operations that update multiple related records, such as email verification,
password reset, password change, account deletion, and role or permission
assignment.

A conforming store must commit when the block finishes successfully and roll
back every change from the block when an exception is raised. Nested
`transaction()` calls must participate in the outer transaction.

A `nullcontext()` can be useful in an early prototype or a deliberately simple
test double, but it does not satisfy the complete `UserStore` contract and will
not pass the shared transaction tests.

### Testing

Every `UserStore` integration should run the shared contract tests provided by
UserHarbor. Import the complete suite in one test module:

```python
# tests/test_user_store_contract.py

from userharbor.testing.user_store_contract import *  # noqa: F403
```

Then provide a function-scoped `user_store` fixture in the integration:

```python
# tests/conftest.py

import pytest


@pytest.fixture
def user_store():
    store = create_user_store()
    try:
        yield store
    finally:
        dispose_user_store(store)
```

The fixture must provide a clean store for every test and release any database
connections or other resources afterwards. The shared suite verifies users,
password hashes, paginated user listings, verification and reset tokens,
sessions, roles, permissions, assignments, and transaction behavior through the
public `UserStore` interface.

Keep backend-specific tests in the integration repository. Examples include
database schema and migration tests, provider-specific errors, custom model
mapping, connection handling, and backend-specific transaction behavior.

See [UserStore contract tests](../Development/contract-tests.md) for instructions
on developing contracts and testing them against a local UserHarbor checkout
before a new version is published.

### Start from the template

[`userharbor-inmemory`](https://github.com/userharbor/userharbor-inmemory) is a minimal, contract-tested `UserStore` implementation and an official GitHub template for building custom storage integrations. It contains a complete in-memory store, package metadata, test and publishing workflows, and the shared contract setup described above.

Select **Use this template** in the repository or open [Create a new repository from the template](https://github.com/new?template_name=userharbor-inmemory&template_owner=userharbor). The generated project starts with a passing contract suite, so the in-memory implementation can be replaced incrementally while the tests continue to verify the required behavior.

After creating a repository:

1. Rename the distribution, import package, store class, and project metadata.
2. Replace the in-memory dictionaries and snapshot transaction with the target backend.
3. Update the `user_store` fixture to create a clean backend and dispose of its resources after every test.
4. Keep the shared contract import and add separate tests for backend-specific schema, errors, mapping, connection, and transaction behavior.

The package can also be installed directly for application tests and examples:

```bash
pip install userharbor-inmemory
```

```python
from userharbor_inmemory import InMemoryUserStore


store = InMemoryUserStore()
```

Each store instance starts empty and retains data only for its own lifetime. It does not provide persistent storage, cross-process sharing, durable transactions, or concurrency guarantees, so it should not be used as a production database.

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

    def send_email_verified(self, username: str, email: str) -> None:
        ...

    def send_password_changed(self, username: str, email: str) -> None:
        ...

    def send_account_deleted(self, username: str, email: str) -> None:
        ...
```

An `EmailSender` should only send messages. It should not decide whether a token
is valid, hash tokens, verify users, or reset passwords. Those responsibilities
belong to UserHarbor core.

### Testing

For `EmailSender`, cover:

* verification messages
* password reset messages
* email-verified messages
* password-changed messages
* account-deleted messages
* subject and sender configuration
* template rendering, if templates are supported
* provider authentication or API calls using fakes

## Framework integrations

Framework integrations should compose UserHarbor with framework-specific tools
instead of moving domain behavior into the framework package.

A framework adapter may provide:

* dependency helpers
* route or router factories
* request-to-command mapping
* response models
* examples for configuring stores and email senders

It should avoid hard-coding one database or email provider unless that is the
explicit purpose of the package. Prefer accepting a configured `UserHarbor`
instance or accepting `UserStore` and `EmailSender` implementations from the
application.

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
