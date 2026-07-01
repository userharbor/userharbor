---
title: FastAPI Integration
description: Add UserHarbor authentication routes and dependencies to FastAPI.
icon: lucide/route

---
# FastAPI Integration

`userharbor-fastapi` provides a FastAPI adapter for UserHarbor. It exposes
account-management routes and dependency helpers while keeping user storage,
email delivery, password hashing, token generation, and account rules in
UserHarbor core and the configured integrations.

Repository:

```text
https://github.com/userharbor/userharbor-fastapi
```

## Installation

```bash
pip install userharbor-fastapi
```

You can also install it through the core package extra:

```bash
pip install "userharbor[fastapi]"
```

The package depends on `userharbor` and FastAPI.

Install storage and email adapters separately. For example:

```bash
pip install userharbor-sqlalchemy
pip install userharbor-smtp
```

## What it provides

The adapter provides:

* a FastAPI `APIRouter`
* account routes for registration, email verification, login, logout, password
  reset, password change, and account deletion
* bearer session token authentication
* current-user and optional-user dependencies
* role and permission dependencies
* UserHarbor exception to HTTP error mapping
* configurable user serialization for route responses

It does not provide a database implementation or email delivery implementation.
Pass a configured `UserHarbor` instance that already has a `UserStore` and
`EmailSender`.

## Basic usage

```python
from fastapi import Depends, FastAPI
from userharbor import UserHarbor
from userharbor_fastapi import UserHarborFastAPI


harbor = UserHarbor(
    secret_key="your-secret-key",
    store=store,
    email_sender=email_sender,
)

auth = UserHarborFastAPI(harbor)

app = FastAPI()
app.include_router(auth.router, prefix="/auth", tags=["auth"])


@app.get("/me")
def me(user=Depends(auth.current_user)):
    return user


@app.get("/admin")
def admin(user=Depends(auth.require_role("admin"))):
    return user


@app.get("/billing")
def billing(user=Depends(auth.require_permission("billing.read"))):
    return user
```

## Built-in routes

The adapter exposes these routes through `auth.router`:

```text
POST   /register
POST   /verify-email
POST   /resend-verification
POST   /login
POST   /logout
POST   /logout-all
GET    /me
POST   /password-reset/request
POST   /password-reset/confirm
POST   /password/change
DELETE /account
```

Mount the router under the prefix used by your application:

```python
app.include_router(auth.router, prefix="/auth", tags=["auth"])
```

With that prefix, the login route is available at `/auth/login`, the current
user route at `/auth/me`, and so on.

## Authentication

`POST /login` returns a bearer-compatible response:

```json
{
  "access_token": "session-token",
  "token_type": "bearer"
}
```

Send the session token on protected requests:

```http
Authorization: Bearer <session-token>
```

The token is the UserHarbor session token returned by `harbor.login()`.

## Dependencies

Use `auth.current_user` when a route requires a valid session:

```python
@app.get("/account")
def account(user=Depends(auth.current_user)):
    return user
```

Use `auth.optional_user` when authentication should be optional:

```python
@app.get("/homepage")
def homepage(user=Depends(auth.optional_user)):
    return {"authenticated": user is not None}
```

Use role and permission dependencies for authorization:

```python
@app.get("/admin")
def admin(user=Depends(auth.require_role("admin"))):
    return user


@app.get("/invoices")
def invoices(user=Depends(auth.require_permission("billing.invoices.read"))):
    return user
```

`auth.require_role()` and `auth.require_permission()` return the current user
when authorization succeeds. They map invalid or expired sessions to
authentication errors and missing roles or permissions to authorization errors.

## User serialization

By default, `/me` returns the public UserHarbor user fields:

```json
{
  "username": "jane",
  "email": "jane@example.com",
  "verified": true
}
```

Pass `user_serializer` when your application returns a richer user object from
its store and wants to expose a custom public response shape:

```python
auth = UserHarborFastAPI(
    harbor,
    user_serializer=lambda user: {
        "username": user.username,
        "email": user.email,
        "verified": user.verified,
        "display_name": user.display_name,
    },
)
```

The serializer is used by the built-in `/me` route.

## Error responses

UserHarbor exceptions are converted into structured FastAPI errors:

```json
{
  "detail": {
    "detail": "Invalid username or password",
    "code": "invalid_credentials"
  }
}
```

The adapter maps common failures as follows:

* invalid credentials and invalid sessions return `401 Unauthorized`
* valid sessions without the required role or permission return
  `403 Forbidden`
* unknown roles and permissions return `404 Not Found`
* invalid input and invalid verification or password reset tokens return
  `400 Bad Request`
* username conflicts return `409 Conflict`

## Combining official adapters

A typical FastAPI application can combine the official SQLAlchemy, SMTP, and
FastAPI integrations:

```python
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from userharbor import UserHarbor
from userharbor_fastapi import UserHarborFastAPI
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

auth = UserHarborFastAPI(harbor)

app = FastAPI()
app.include_router(auth.router, prefix="/auth", tags=["auth"])
```

In production applications, use your normal configuration system for secrets,
SMTP credentials, and database URLs.
