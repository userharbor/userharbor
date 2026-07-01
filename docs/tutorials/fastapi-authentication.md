---
title: FastAPI Authentication with UserHarbor
description: Build FastAPI authentication routes with UserHarbor.
icon: lucide/route

---
# FastAPI Authentication with UserHarbor

!!! note
    For most FastAPI applications, prefer the ready-made
    [`userharbor-fastapi`](../integrations/fastapi.md) adapter. It provides the
    router, dependencies, schemas, and HTTP error mapping shown in this tutorial.

This tutorial builds the same ideas step by step.

You will create a small FastAPI application that uses UserHarbor directly for:

* user registration
* email verification
* login
* bearer session authentication
* current-user dependencies
* password reset
* password change
* account deletion
* logout
* role and permission checks

The goal is to show how the pieces fit together. UserHarbor owns the account
rules, password hashing, token generation, token hashing, session validation,
and role checks. FastAPI owns HTTP routing, request parsing, response models,
and dependency injection.

## Install dependencies

Create a virtual environment, then install FastAPI, UserHarbor, and a storage
adapter:

```bash
pip install "fastapi[standard]"
pip install userharbor
pip install userharbor-sqlalchemy
```

This tutorial uses the SQLAlchemy store and a small console email sender. In a
real application, use your normal database configuration and an email sender
such as [`userharbor-smtp`](../integrations/smtp.md).

## Create `main.py`

Start with the imports and application setup:

```python
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from userharbor import UserHarbor
from userharbor.exceptions import (
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidPasswordResetTokenError,
    InvalidPermissionError,
    InvalidRoleError,
    InvalidSessionTokenError,
    InvalidUsernameError,
    InvalidVerificationTokenError,
    PermissionDeniedError,
    UnknownPermissionError,
    UnknownRoleError,
    UnverifiedUserError,
    UserHarborError,
    WeakPasswordError,
)
from userharbor_sqlalchemy import SQLAlchemyUserStore


app = FastAPI()
bearer = HTTPBearer(auto_error=False)
```

`HTTPBearer(auto_error=False)` lets your code decide exactly how to turn missing
or invalid credentials into HTTP responses.

## Add an email sender

UserHarbor calls an `EmailSender` when it needs to send verification tokens,
password reset tokens, and account notifications.

For the tutorial, print those messages to the terminal:

```python
class ConsoleEmailSender:
    def send_verification(
        self,
        username: str,
        email: str,
        verification_token: str,
    ) -> None:
        print(f"Verify {username} at {email}: {verification_token}")

    def send_password_reset(
        self,
        username: str,
        email: str,
        reset_token: str,
    ) -> None:
        print(f"Reset password for {username} at {email}: {reset_token}")

    def send_email_verified(self, username: str, email: str) -> None:
        print(f"Email verified for {username} at {email}")

    def send_password_changed(self, username: str, email: str) -> None:
        print(f"Password changed for {username} at {email}")

    def send_account_deleted(self, username: str, email: str) -> None:
        print(f"Account deleted for {username} at {email}")
```

In production, replace this with an implementation that sends real email.

## Configure UserHarbor

Create the SQLAlchemy store, create the tables, and pass the store and email
sender to `UserHarbor`:

```python
engine = create_engine("sqlite:///users.db")
SessionLocal = sessionmaker(bind=engine)

store = SQLAlchemyUserStore(SessionLocal)
store.metadata.create_all(engine)

harbor = UserHarbor(
    secret_key="change-this-secret-key",
    store=store,
    email_sender=ConsoleEmailSender(),
)
```

The FastAPI application never handles password hashing or token hashing.
UserHarbor does that before data reaches the store.

## Define request and response models

Use Pydantic models for the HTTP layer:

```python
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class DeleteAccountRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PublicUser(BaseModel):
    username: str
    email: str
    verified: bool
```

These models are not part of UserHarbor. They are your HTTP contract.

## Map UserHarbor errors to HTTP errors

UserHarbor raises domain exceptions. Your web layer should translate them into
HTTP responses:

```python
ERROR_CODES: dict[type[UserHarborError], str] = {
    InvalidCredentialsError: "invalid_credentials",
    InvalidEmailError: "invalid_email",
    InvalidPasswordResetTokenError: "invalid_password_reset_token",
    InvalidPermissionError: "invalid_permission",
    InvalidRoleError: "invalid_role",
    InvalidSessionTokenError: "invalid_session_token",
    InvalidUsernameError: "invalid_username",
    InvalidVerificationTokenError: "invalid_verification_token",
    PermissionDeniedError: "permission_denied",
    UnknownPermissionError: "unknown_permission",
    UnknownRoleError: "unknown_role",
    UnverifiedUserError: "unverified_user",
    WeakPasswordError: "weak_password",
}


def error_code(error: UserHarborError) -> str:
    for error_type, code in ERROR_CODES.items():
        if isinstance(error, error_type):
            return code
    return "userharbor_error"


def status_code(error: UserHarborError) -> int:
    if isinstance(error, (InvalidCredentialsError, InvalidSessionTokenError)):
        return status.HTTP_401_UNAUTHORIZED
    if isinstance(error, (PermissionDeniedError, UnverifiedUserError)):
        return status.HTTP_403_FORBIDDEN
    if isinstance(error, (UnknownPermissionError, UnknownRoleError)):
        return status.HTTP_404_NOT_FOUND
    if isinstance(error, InvalidUsernameError) and "already exists" in str(error):
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST


def to_http_error(error: UserHarborError) -> HTTPException:
    return HTTPException(
        status_code=status_code(error),
        detail={
            "detail": str(error) or error.__class__.__name__,
            "code": error_code(error),
        },
        headers={"WWW-Authenticate": "Bearer"}
        if isinstance(error, InvalidSessionTokenError)
        else None,
    )
```

This keeps authentication failures, authorization failures, and validation
errors distinct.

## Register users

The registration endpoint parses JSON, calls `harbor.register()`, and returns a
neutral response:

```python
@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest) -> dict[str, str]:
    try:
        harbor.register(
            username=request.username,
            email=request.email,
            password=request.password,
        )
    except UserHarborError as error:
        raise to_http_error(error) from error
    return {"detail": "User registered"}
```

UserHarbor validates the username, email, and password. It creates the user,
stores only the password hash, stores only the verification token hash, and calls
the email sender with the raw verification token.

## Verify email addresses

Copy the verification token printed by `ConsoleEmailSender` and send it to this
endpoint:

```python
@app.post("/auth/verify-email")
def verify_email(request: VerifyEmailRequest) -> dict[str, str]:
    try:
        harbor.verify_email(request.token)
    except UserHarborError as error:
        raise to_http_error(error) from error
    return {"detail": "Email verified"}
```

After verification, the user can log in.

## Login and return a bearer token

Call `harbor.login()` and return the session token in a bearer-compatible
response:

```python
@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    try:
        session_token = harbor.login(request.username, request.password)
    except UserHarborError as error:
        raise to_http_error(error) from error
    return TokenResponse(access_token=session_token)
```

The raw session token is returned to the client once. UserHarbor stores a hash
of it through the configured store.

Clients should send the token on later requests:

```http
Authorization: Bearer <session-token>
```

## Create current-user dependencies

Now create the dependency that reads the bearer token and asks UserHarbor for the
current user:

```python
def get_session_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_current_user(token: str = Depends(get_session_token)) -> Any:
    try:
        return harbor.get_current_user(token)
    except UserHarborError as error:
        raise to_http_error(error) from error
```

This is the main connection between FastAPI security dependencies and
UserHarbor session validation.

## Protect a route

Use `Depends(get_current_user)` in any route that requires authentication:

```python
def serialize_user(user: Any) -> PublicUser:
    return PublicUser(
        username=user.username,
        email=user.email,
        verified=user.verified,
    )


@app.get("/auth/me", response_model=PublicUser)
def me(user: Any = Depends(get_current_user)) -> PublicUser:
    return serialize_user(user)
```

If the token is missing, invalid, expired, or points to a deleted user,
UserHarbor rejects it.

## Logout

Logout removes the current session token:

```python
@app.post("/auth/logout")
def logout(token: str = Depends(get_session_token)) -> dict[str, str]:
    try:
        harbor.logout(token)
    except UserHarborError as error:
        raise to_http_error(error) from error
    return {"detail": "Logged out"}
```

To remove all sessions for the current user:

```python
@app.post("/auth/logout-all")
def logout_all(token: str = Depends(get_session_token)) -> dict[str, str]:
    try:
        harbor.logout_all(token)
    except UserHarborError as error:
        raise to_http_error(error) from error
    return {"detail": "Logged out from all sessions"}
```

## Password reset

Password reset is split into two routes. The first route sends a reset token if
the email belongs to a user:

```python
@app.post("/auth/password-reset/request")
def request_password_reset(request: PasswordResetRequest) -> dict[str, str]:
    try:
        harbor.send_password_reset(request.email)
    except UserHarborError as error:
        raise to_http_error(error) from error
    return {"detail": "Password reset email sent"}
```

UserHarbor returns neutrally for unknown email addresses, helping reduce email
enumeration.

The second route accepts the reset token and the new password:

```python
@app.post("/auth/password-reset/confirm")
def confirm_password_reset(request: PasswordResetConfirmRequest) -> dict[str, str]:
    try:
        harbor.reset_password(
            new_password=request.new_password,
            reset_token=request.token,
        )
    except UserHarborError as error:
        raise to_http_error(error) from error
    return {"detail": "Password reset"}
```

After a successful reset, UserHarbor removes all sessions for that user.

## Password change

Password change requires an existing session and the current password:

```python
@app.post("/auth/password/change")
def change_password(
    request: ChangePasswordRequest,
    token: str = Depends(get_session_token),
) -> dict[str, str]:
    try:
        harbor.change_password(
            old_password=request.old_password,
            new_password=request.new_password,
            session_token=token,
        )
    except UserHarborError as error:
        raise to_http_error(error) from error
    return {"detail": "Password changed"}
```

UserHarbor invalidates all sessions after a successful password change.

## Delete accounts

Account deletion should require both a valid session and the current password:

```python
@app.delete("/auth/account")
def delete_account(
    request: DeleteAccountRequest,
    token: str = Depends(get_session_token),
) -> dict[str, str]:
    try:
        harbor.delete_account(
            password=request.password,
            session_token=token,
        )
    except UserHarborError as error:
        raise to_http_error(error) from error
    return {"detail": "Account deleted"}
```

UserHarbor removes all sessions before deleting the user and then calls the
email sender with an account-deleted notification.

## Add role and permission dependencies

Create a dependency factory for permissions:

```python
def require_permission(permission: str):
    def dependency(token: str = Depends(get_session_token)) -> Any:
        try:
            return harbor.require_permission(token, permission)
        except UserHarborError as error:
            raise to_http_error(error) from error

    return dependency
```

Use it on protected routes:

```python
@app.get("/admin/users")
def list_users(
    user: Any = Depends(require_permission("users.read")),
) -> dict[str, str]:
    return {"detail": f"{user.username} can read users"}
```

Before this can succeed, the permission and role must exist and the user must
have the role:

```python
harbor.roles.create("admin")
harbor.permissions.create("users.read")
harbor.roles.grant_permission("admin", "users.read")
harbor.grant_role("jane", "admin")
```

In a real application, put that setup in migrations, admin commands, or an
internal admin interface.

## Production hardening checklist

This tutorial keeps everything in one file so the flow is easy to inspect. For a
real application:

* load `secret_key`, database URLs, and SMTP credentials from environment
  variables or a secret manager
* use a long random `secret_key` and rotate it carefully, because it is used for
  token hashing
* serve the API only over HTTPS
* replace `ConsoleEmailSender` with a real email sender
* use migrations instead of `store.metadata.create_all(engine)` at runtime
* decide where roles and permissions are created, such as migrations or admin
  commands
* keep bearer tokens out of logs
* configure CORS explicitly if a browser frontend calls the API
* add rate limiting around login, password reset, and verification resend
* return neutral responses for account discovery-sensitive flows
* write tests for successful flows and for each mapped error response

## Run the app

Run the application:

```bash
fastapi dev main.py
```

Open the interactive docs:

```text
http://127.0.0.1:8000/docs
```

Then try this flow:

1. Call `POST /auth/register`
2. Copy the verification token printed in the terminal
3. Call `POST /auth/verify-email`
4. Call `POST /auth/login`
5. Copy the returned `access_token`
6. Send it as `Authorization: Bearer <token>`
7. Call `GET /auth/me`

## What you built

You now have a FastAPI application that uses UserHarbor directly.

FastAPI handles:

* routing
* request parsing
* response models
* OpenAPI documentation
* dependency injection
* HTTP status codes

UserHarbor handles:

* account validation
* password hashing
* token generation
* token hashing before storage
* email verification
* session validation
* password reset and password change flows
* role and permission checks

This is the same boundary used by the
[`userharbor-fastapi`](../integrations/fastapi.md) adapter. The adapter simply
packages this wiring so applications do not have to repeat it.
