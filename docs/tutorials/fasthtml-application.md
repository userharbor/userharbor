---
title: FastHTML Application with UserHarbor
description: Build a complete hypermedia-driven application with FastHTML, HTMX, Basecoat, and UserHarbor.
icon: lucide/app-window

---
# FastHTML Application with UserHarbor

This tutorial builds a [Hypermedia-Driven Application (HDA)](https://htmx.org/essays/hypermedia-driven-applications/)
with [FastHTML](https://github.com/AnswerDotAI/fasthtml),
[HTMX](https://github.com/bigskysoftware/htmx), and
[UserHarbor](https://github.com/userharbor/userharbor).
The server returns HTML, and the browser updates the page through HTMX attributes.

## What you will build

You will create an application with registration, email verification, login,
password recovery, a paginated user list, user details, password changes, and
account deletion. Only the account owner sees their password and deletion forms.
[Basecoat](https://github.com/hunvreus/basecoat) provides the UI components.

<video controls preload="metadata" playsinline style="width: 100%; border-radius: 0.5rem;" aria-label="FastHTML Starter presentation">
  <source src="https://github.com/user-attachments/assets/1bcafdda-fe51-4bb3-a3e7-cb1302952d13" type="video/mp4">
  <a href="https://github.com/userharbor/fasthtml-starter/blob/master/presentation.mp4">Watch the presentation</a>.
</video>

!!! tip "Start with the finished application"
    Use [FastHTML Starter](https://github.com/userharbor/fasthtml-starter) as a
    repository template if you want to run the finished application immediately.
    Its README contains the setup instructions. This walkthrough explains how
    to build the same account flows, with a smaller dashboard layout.

FastHTML handles routing, form parsing, and HTML rendering. HTMX sends requests
and swaps HTML. UserHarbor handles account validation, password hashing, tokens,
sessions, and account operations. Your application decides who may access each page.

## Install dependencies

Use Python 3.14 or later, matching the starter, and
[uv](https://github.com/astral-sh/uv):

```bash
uv init --python 3.14 fasthtml-app
cd fasthtml-app
uv add python-fasthtml "userharbor[sqlalchemy,smtp]" \
  fasthtml-basecoatui "fasthtml-tailwindcss[dev]" \
  fasthtml-lucide
```

The Python wrappers
[fasthtml-basecoatui](https://github.com/SpaceShaman/fasthtml-basecoat),
[fasthtml-tailwindcss](https://github.com/SpaceShaman/fasthtml-tailwindcss), and
[fasthtml-lucide](https://github.com/SpaceShaman/fasthtml-lucide) provide UI
components, stylesheet generation, and icons. No separate JavaScript application
or JSON API is needed for these flows.

## Organize the application

Use the same separation as the starter:

```text
app/
├── core/             # Settings, UserHarbor instance, shared types
├── components/       # Forms, cards, table, pagination, alerts
│   └── auth/
├── layouts/          # HTML document and page shells
├── pages/            # Components composed into complete pages
├── routes/           # Request parsing and domain calls
├── email_templates/  # Verification and recovery links
├── static/
└── main.py           # Session middleware and mounted applications
```

Create the directories and package files:

```bash
mkdir -p app/core app/components/auth app/layouts app/pages app/routes \
  app/email_templates app/static
touch app/__init__.py app/core/__init__.py app/components/__init__.py \
  app/components/auth/__init__.py app/layouts/__init__.py \
  app/pages/__init__.py app/routes/__init__.py
```

Save each code block in the file named above it. When a step says to append code,
keep the preceding contents of that file. Finish creating the files before starting
the application: routes import pages, and pages import their components.

## Configure settings and UserHarbor

Create `.env` at the project root. Choose a random secret key and fill in your SMTP
credentials. `APP_URL` is the public base URL used in email links.

```dotenv title=".env"
SECRET_KEY=replace-with-a-long-random-secret
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=noreply@example.com
APP_URL=http://localhost:8000
```

Keep `.env` out of version control. The run command at the end loads it into the
process environment. Read those settings in `app/core/settings.py`:

```python title="app/core/settings.py"
import os

SECRET_KEY = os.environ["SECRET_KEY"]
SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.environ["SMTP_FROM_EMAIL"]
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
```

Configure one shared `UserHarbor` instance. The
[SQLAlchemy adapter](../integrations/sqlalchemy.md) persists accounts and sessions,
and the [SMTP adapter](../integrations/smtp.md) sends account emails.

The SQLite URL is relative to the working directory, so running from `app/`
creates `app/users.db`. `create_all()` creates the tables on the first run.

```python title="app/core/harbor.py"
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from userharbor import UserHarbor
from userharbor_smtp import SMTPEmailSender
from userharbor_sqlalchemy import SQLAlchemyUserStore

from .settings import (
    APP_URL,
    SECRET_KEY,
    SMTP_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
)

engine = create_engine("sqlite:///users.db")
SessionLocal = sessionmaker(bind=engine)

store = SQLAlchemyUserStore(SessionLocal)
store.metadata.create_all(engine)

email_sender = SMTPEmailSender(
    host=SMTP_HOST,
    port=SMTP_PORT,
    username=SMTP_USERNAME,
    password=SMTP_PASSWORD,
    from_email=SMTP_FROM_EMAIL,
    template_dir=Path(__file__).parent.parent / "email_templates",
    template_context={
        "app_url": APP_URL,
    },
)

harbor = UserHarbor(
    secret_key=SECRET_KEY,
    store=store,
    email_sender=email_sender,
)
```

The custom email directory can override individual templates. Add these two
files so verification and recovery messages point to our routes. Other account
notifications use the SMTP adapter's default templates.

```html title="app/email_templates/verification.html"
<p>Hello {{ username }},</p>
<p>
  <a href="{{ app_url.rstrip('/') }}/auth/verify_email?token={{ token | urlencode }}">Activate your account</a>
</p>
```

```html title="app/email_templates/password_reset.html"
<p>Hello {{ username }},</p>
<p>
  <a href="{{ app_url.rstrip('/') }}/auth/reset_password?token={{ token | urlencode }}">Reset your password</a>
</p>
```

Define the return type used by routes. A route can return HTML, a response, or
HTML together with HTMX response headers. `UserLike` describes the public user
fields; it does not expose the password hash.

```python title="app/core/types.py"
from fasthtml.common import FT, HttpHeader, Response
from userharbor.interfaces import UserLike

type HTMLResult = FT | Response | tuple[FT | HttpHeader, ...]
User = UserLike
```

## Build the shared layouts

### HTML document, assets, and loading indicator

Every page uses `BaseLayout`. It loads HTMX, Basecoat's JavaScript, and the
stylesheet generated from Basecoat's `nova` theme. The Tailwind development
integration builds the CSS and watches for class changes while the app runs.

`hx_boost="true"` lets ordinary internal links navigate through HTMX. They still
have real URLs, including pagination query parameters. A boosted link normally
replaces the body contents and updates browser history.

The single `Spinner` has `htmx-indicator`, which hides it while idle.
`hx_indicator` is inherited from the body, so forms and links use this indicator
without repeating its selector. The `#alerts` container receives feedback from
any form.

```python title="app/layouts/base.py"
from fasthtml.common import (
    FT,
    Body,
    Div,
    Head,
    Html,
    Meta,
    Script,
    Title,
)
from fasthtml_basecoat import (
    BasecoatInput,
    BasecoatJS,
    Spinner,
)
from fasthtml_tailwindcss import TailwindHead


def BaseLayout(*c, title: str, **kwargs) -> FT:
    return Html(
        Head(
            Title(title),
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Script(src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.11/dist/htmx.js"),
            BasecoatJS(),
            TailwindHead(input=BasecoatInput("nova"), watch=True),
        ),
        Body(
            Spinner(
                id="global-spinner",
                cls="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 pointer-events-none size-10 htmx-indicator",
            ),
            Div(
                id="alerts",
                cls="fixed top-4 inset-x-0 z-50 flex flex-col items-center gap-4",
            ),
            *c,
            hx_boost="true",
            hx_indicator="#global-spinner",
        ),
        **kwargs,
    )
```

### Authentication and dashboard shells

The authentication layout adds a theme switcher. Cards will handle the actual
forms and messages.

```python title="app/layouts/auth.py"
from fasthtml.common import (
    FT,
    Div,
)
from fasthtml_basecoat import (
    ThemeSwitcher,
)

from .base import BaseLayout


def AuthLayout(*c, title: str, **kwargs) -> FT:
    return BaseLayout(
        Div(
            ThemeSwitcher(),
            cls="fixed top-4 right-4 z-50 flex items-center gap-4",
        ),
        *c,
        title=title,
        **kwargs,
    )
```

For the dashboard, keep a small header containing the current user's profile
link and a logout button. This tutorial uses a compact shell; the starter adds
a responsive sidebar and a fuller navigation bar.

```python title="app/layouts/dashboard.py"
from urllib.parse import quote

from core.types import User
from fasthtml.common import FT, A, Div, Header, Main, Span
from fasthtml_basecoat import Button, ThemeSwitcher

from .base import BaseLayout


def DashboardLayout(*c, title: str, user: User) -> FT:
    return BaseLayout(
        Header(
            A("Users", href="/"),
            Span(title),
            A(user.username, href=f"/users/{quote(user.username, safe='')}"),
            Button(
                "Logout",
                type="button",
                variant="ghost",
                hx_post="/auth/logout",
                hx_swap="none",
                hx_disabled_elt="this",
            ),
            ThemeSwitcher(variant="ghost"),
            cls="flex flex-wrap items-center gap-4 border-b px-4 py-4",
        ),
        Main(
            Div(*c, cls="mx-auto max-w-6xl space-y-6 px-4 py-8"),
            id="dashboard-content",
        ),
        title=title,
    )
```

## Return form feedback as HTML

Create a shared `Alert` component. The outer element uses
`hx_swap_oob="beforeend:#alerts"`, so HTMX appends the returned message to the
layout's alert container even when a form uses `hx_swap="none"`.

Domain errors can therefore be displayed without replacing the form or erasing
the user's input. `UserHarborError` remains a domain exception; rendering the
message is the application's responsibility.

```python title="app/components/alert.py"
from typing import Literal

from fasthtml.common import FT, H2, Div, Footer, Section
from fasthtml_basecoat import Button
from fasthtml_lucide import Icon


def Alert(heading: str, message: str, variant: Literal["info", "error"]) -> FT:
    return Div(
        Div(
            Icon("info"),
            H2(heading),
            Section(message),
            Footer(
                Button(
                    Icon("circle-x"),
                    aria_label="Close",
                    data_tooltip="Close",
                    data_side="bottom",
                    data_variant="ghost",
                    onclick="this.closest('.alert').remove()",
                ),
            ),
            cls="alert w-full max-w-md",
            data_variant="destructive" if variant == "error" else None,
            hx_on__load="setTimeout(() => { this.remove() }, 10000)",
        ),
        hx_swap_oob="beforeend:#alerts",
    )
```

## Create the authentication forms

### Login

Each input's `name` matches a route parameter. FastHTML reads the submitted values
and passes them to the handler. Basecoat's `Input`, `Label`, `Button`, and `Card`
wrappers produce the HTML and styling.

`hx_post` sends the form to the handler. `hx_swap="none"` prevents the ordinary
response swap; alerts and explicit response headers control the visible result.
The `hx_disabled_elt` selector disables the form's inputs and buttons during the
request. It uses a unique form ID, so another form on the page remains usable.

The recovery link switches the Basecoat tabs to the hidden recovery panel.

```python title="app/components/auth/login.py"
from fasthtml.common import FT, H2, A, Div, Form, Header, P, Section
from fasthtml_basecoat import (
    Button,
    Card,
    Input,
    Label,
)


def LoginCard(**attrs) -> FT:
    return Card(
        Header(
            H2("Login to your account"),
            P("Enter your credentials to access your account."),
        ),
        Section(_LoginForm()),
        **attrs,
    )


def _LoginForm() -> FT:
    return Form(
        Div(
            Label("Username", fr="username"),
            Input(
                type="text",
                id="username",
                name="username",
                required=True,
            ),
            cls="grid gap-2",
        ),
        Div(
            Div(
                Label("Password", fr="password"),
                A(
                    "Forgot your password?",
                    onclick="event.preventDefault(); this.closest('.tabs').select(document.getElementById('auth-forgot-password-tab'));",
                    cls="ms-auto inline-block text-sm underline-offset-4 hover:underline",
                ),
                cls="flex items-center",
            ),
            Input(
                type="password",
                id="password",
                name="password",
                required=True,
            ),
            cls="grid gap-2",
        ),
        Button("Login", cls="w-full"),
        cls="grid gap-6",
        id="login-form",
        hx_post="login",
        hx_disabled_elt="#login-form input, #login-form button",
        hx_swap="none",
    )
```

### Registration

The success response replaces the registration card through `HX-Retarget` and
`HX-Reswap`. These response headers override the form's default swap behavior.
Keep the panel ID and tab attributes on the replacement so Basecoat's tabs can
continue to find it.

```python title="app/components/auth/register.py"
from core.types import HTMLResult
from fasthtml import HttpHeader
from fasthtml.common import FT, H2, Div, Form, Header, P, Section
from fasthtml_basecoat import Button, Card, Input, Label


def RegisterCard(**attrs) -> FT:
    return Card(
        Header(
            H2("Create an account"),
            P("Enter your details to create your account."),
        ),
        Section(_RegisterForm()),
        **attrs,
    )


def SuccessfulRegisterCard() -> HTMLResult:
    return (
        Card(
            Header(
                H2("Registration Successful"),
                P("Please check your email to verify your account."),
            ),
            cls="w-full max-w-sm text-center",
            id="auth-register-card",
            role="tabpanel",
            aria_labelledby="auth-register-tab",
        ),
        HttpHeader("HX-Retarget", "#auth-register-card"),
        HttpHeader("HX-Reswap", "outerHTML"),
    )


def _RegisterForm() -> FT:
    return Form(
        Div(
            Label("Username", fr="register-username"),
            Input(
                type="text",
                id="register-username",
                name="username",
                autocomplete="username",
                required=True,
            ),
            cls="grid gap-2",
        ),
        Div(
            Label("Email", fr="register-email"),
            Input(
                type="email",
                id="register-email",
                name="email",
                autocomplete="email",
                required=True,
            ),
            cls="grid gap-2",
        ),
        Div(
            Label("Password", fr="register-password"),
            Input(
                type="password",
                id="register-password",
                name="password",
                autocomplete="new-password",
                required=True,
            ),
            cls="grid gap-2",
        ),
        Button("Create account", cls="w-full"),
        cls="grid gap-6",
        id="register-form",
        hx_post="register",
        hx_disabled_elt="#register-form input, #register-form button",
        hx_swap="none",
    )
```

### Request a password reset

The recovery form asks only for an email address. Its success message is neutral:
it does not disclose whether that address belongs to an account.

```python title="app/components/auth/forgot_password.py"
from core.types import HTMLResult
from fasthtml.common import FT, H2, Div, Form, Header, HttpHeader, P, Section
from fasthtml_basecoat import Button, Card, Input, Label


def ForgotPasswordCard(**attrs) -> FT:
    return Card(
        Header(
            H2("Forgot your password?"),
            P("Enter your email address to receive password reset instructions."),
        ),
        Section(_ForgotPasswordForm()),
        **attrs,
    )


def SuccessfulForgotPasswordCard() -> HTMLResult:
    return (
        Card(
            Header(
                H2("Check your email"),
                P(
                    "If an account exists for this email, you will receive password reset instructions."
                ),
            ),
            cls="text-center",
            id="auth-forgot-password-card",
            role="tabpanel",
            aria_labelledby="auth-forgot-password-tab",
        ),
        HttpHeader("HX-Retarget", "#auth-forgot-password-card"),
        HttpHeader("HX-Reswap", "outerHTML"),
    )


def _ForgotPasswordForm() -> FT:
    return Form(
        Div(
            Label("Email", fr="forgot-password-email"),
            Input(
                type="email",
                id="forgot-password-email",
                name="email",
                autocomplete="email",
                required=True,
            ),
            cls="grid gap-2",
        ),
        Button("Send reset instructions", cls="w-full"),
        cls="grid gap-6",
        id="forgot-password-form",
        hx_post="forgot_password",
        hx_disabled_elt="#forgot-password-form input, #forgot-password-form button",
        hx_swap="none",
    )
```

### Enter a new password

The reset form carries the email token in a hidden input. `autocomplete="new-password"`
tells password managers that these fields contain a new password. The route will
also compare the two submitted values.

```python title="app/components/auth/reset_password.py"
from core.types import HTMLResult
from fasthtml.common import FT, H2, A, Div, Form, Header, HttpHeader, P, Section
from fasthtml_basecoat import Button, Card, Input, Label


def ResetPasswordCard(token: str, **attrs) -> FT:
    return Card(
        Header(
            H2("Reset your password"),
            P("Enter and confirm your new password."),
        ),
        Section(_ResetPasswordForm(token)),
        **attrs,
    )


def SuccessfulResetPasswordCard() -> HTMLResult:
    return (
        Card(
            Header(
                H2("Password Updated"),
                P("Your password has been updated. You can now log in."),
            ),
            Section(
                A(
                    "Back to login",
                    href="/auth/",
                    cls="text-sm underline underline-offset-4",
                ),
            ),
            cls="w-full max-w-sm text-center",
            id="reset-password-card",
        ),
        HttpHeader("HX-Retarget", "#reset-password-card"),
        HttpHeader("HX-Reswap", "outerHTML"),
    )


def _ResetPasswordForm(token: str) -> FT:
    return Form(
        Input(type="hidden", name="token", value=token),
        Div(
            Label("New password", fr="new-password"),
            Input(
                type="password",
                id="new-password",
                name="new_password",
                autocomplete="new-password",
                required=True,
            ),
            cls="grid gap-2",
        ),
        Div(
            Label("Confirm password", fr="confirm-password"),
            Input(
                type="password",
                id="confirm-password",
                name="confirm_password",
                autocomplete="new-password",
                required=True,
            ),
            cls="grid gap-2",
        ),
        Button("Reset password", cls="w-full"),
        cls="grid gap-6",
        id="reset-password-form",
        hx_post="/auth/update_password",
        hx_disabled_elt="#reset-password-form input, #reset-password-form button",
        hx_swap="none",
    )
```

### Compose the authentication pages

The login, registration, and recovery cards belong to one Basecoat `Tabs`
component. The `aria_controls` values match their panel IDs. Password reset and
email verification have separate pages because users arrive from email links.

```python title="app/pages/auth.py"
from components.auth.forgot_password import ForgotPasswordCard
from components.auth.login import LoginCard
from components.auth.register import RegisterCard
from fasthtml.common import FT, Button, Div, Nav
from fasthtml_basecoat import (
    Tabs,
)
from layouts.auth import AuthLayout


def AuthPage() -> FT:
    return AuthLayout(
        Div(
            Tabs(
                Nav(
                    Button(
                        "Login",
                        role="tab",
                        id="auth-login-tab",
                        aria_controls="auth-login-card",
                        aria_selected="true",
                        tabindex="0",
                    ),
                    Button(
                        "Sign Up",
                        role="tab",
                        id="auth-register-tab",
                        aria_controls="auth-register-card",
                        aria_selected="false",
                        tabindex="-1",
                    ),
                    Button(
                        "Reset password",
                        role="tab",
                        id="auth-forgot-password-tab",
                        aria_controls="auth-forgot-password-card",
                        aria_selected="false",
                        tabindex="-1",
                        hidden=True,
                    ),
                    role="tablist",
                    aria_label="Account access",
                    cls="w-full",
                ),
                LoginCard(
                    role="tabpanel",
                    id="auth-login-card",
                    aria_labelledby="auth-login-tab",
                ),
                RegisterCard(
                    role="tabpanel",
                    id="auth-register-card",
                    aria_labelledby="auth-register-tab",
                    hidden=True,
                ),
                ForgotPasswordCard(
                    role="tabpanel",
                    id="auth-forgot-password-card",
                    aria_labelledby="auth-forgot-password-tab",
                    hidden=True,
                ),
                id="auth-tabs",
                cls="w-full max-w-sm",
            ),
            cls="min-h-dvh flex items-center justify-center p-4",
        ),
        title="Account access",
    )
```

```python title="app/pages/reset_password.py"
from components.auth.reset_password import ResetPasswordCard
from fasthtml.common import FT, Div
from layouts.auth import AuthLayout


def ResetPasswordPage(token: str) -> FT:
    return AuthLayout(
        Div(
            ResetPasswordCard(
                token,
                id="reset-password-card",
                cls="w-full max-w-sm",
            ),
            cls="min-h-dvh flex items-center justify-center p-4",
        ),
        title="Reset your password",
    )
```

```python title="app/pages/verify_email.py"
from fasthtml.common import FT, H2, A, Div, Header, P, Section
from fasthtml_basecoat import Card
from layouts.auth import AuthLayout


def VerifyEmailPage(error: str | None = None) -> FT:
    title = "Verification Failed" if error is not None else "Account Activated"
    message = error if error is not None else "Your account has been activated."
    return AuthLayout(
        Div(
            Card(
                Header(H2(title), P(message)),
                Section(
                    A(
                        "Back to login",
                        href="/auth/",
                        cls="text-sm underline underline-offset-4",
                    ),
                ),
                cls="w-full max-w-sm text-center",
            ),
            cls="min-h-dvh flex items-center justify-center p-4",
        ),
        title=title,
    )
```

## Connect authentication forms to UserHarbor

Create `app/routes/auth.py`. This is a mounted FastHTML application: its local
`/login` route will be available at `/auth/login` after we mount it.

Start with the imports, router, and page route:

```python title="app/routes/auth.py"
from components.alert import Alert
from components.auth.forgot_password import SuccessfulForgotPasswordCard
from components.auth.register import SuccessfulRegisterCard
from components.auth.reset_password import SuccessfulResetPasswordCard
from core.harbor import harbor
from core.types import HTMLResult
from fasthtml.common import FT, HttpHeader, Response, fast_app
from pages.auth import AuthPage
from pages.reset_password import ResetPasswordPage
from pages.verify_email import VerifyEmailPage
from userharbor.exceptions import UserHarborError

auth_app, rt = fast_app()


@rt(methods=["GET"])
def index() -> FT:
    return AuthPage()
```

### Register and verify an account

Append these handlers to `app/routes/auth.py`. Registration calls
`harbor.register()`, which validates the account, hashes the password, stores the
verification token hash, and sends the verification email.

The email link opens a GET route with `token` in the query string. Successful
verification activates the account so the user can log in. The page avoids
sending the token URL as a referrer and is not cached.

```python title="app/routes/auth.py"
@rt(methods=["POST"])
def register(username: str, email: str, password: str) -> HTMLResult:
    try:
        harbor.register(username, email, password)
    except UserHarborError as e:
        return Alert("Registration Failed", str(e), variant="error")
    return SuccessfulRegisterCard()


@rt(methods=["GET"])
def verify_email(token: str) -> HTMLResult:
    try:
        harbor.verify_email(token)
    except UserHarborError as e:
        page = VerifyEmailPage(error=str(e))
    else:
        page = VerifyEmailPage()
    return (
        page,
        HttpHeader("Referrer-Policy", "no-referrer"),
        HttpHeader("Cache-Control", "no-store"),
    )
```

### Log in with an HttpOnly session cookie

Append the login handler. `harbor.login()` returns the raw session token;
UserHarbor persists its hash. The web application stores the raw token in an
HttpOnly cookie, so page scripts do not need to read it.

A successful HTMX login returns HTTP 200 with `HX-Redirect`, which makes the
browser load `/`. Do not combine this header with a 3xx response: HTMX does not
process response headers on 3xx responses.

`secure=False` is for local HTTP development. Set it to `True` when deploying
behind HTTPS.

```python title="app/routes/auth.py"
@rt(methods=["POST"])
def login(username: str, password: str) -> HTMLResult:
    try:
        session_token = harbor.login(username, password)
    except UserHarborError as e:
        return Alert("Login Failed", str(e), variant="error")
    response = Response(headers={"HX-Redirect": "/"})
    response.set_cookie(
        "session_token",
        session_token,
        path="/",
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
    )
    return response
```

### Log out

Logout should invalidate the server-side session as well as clear the cookie.
An already expired session can be treated as logged out. Append:

```python title="app/routes/auth.py"
@rt(methods=["POST"])
def logout(request) -> HTMLResult:
    try:
        harbor.logout(request.cookies.get("session_token", ""))
    except UserHarborError:
        pass
    response = Response(headers={"HX-Redirect": "/auth/"})
    response.delete_cookie("session_token", path="/")
    return response
```

### Recover a forgotten password

Append the recovery handlers. `harbor.send_password_reset()` sends a token when
the address is known and returns neutrally for unknown addresses. The email link
opens `ResetPasswordPage`; its form submits the token and new password.

`harbor.reset_password()` validates the token and password, changes the password,
and invalidates all sessions for that user. The success card sends the user back
to login.

```python title="app/routes/auth.py"
@rt(methods=["POST"])
def forgot_password(email: str) -> HTMLResult:
    try:
        harbor.send_password_reset(email)
    except UserHarborError as e:
        return Alert("Password Reset Failed", str(e), variant="error")
    return SuccessfulForgotPasswordCard()


@rt(methods=["GET"])
def reset_password(token: str) -> HTMLResult:
    return (
        ResetPasswordPage(token),
        HttpHeader("Referrer-Policy", "no-referrer"),
        HttpHeader("Cache-Control", "no-store"),
    )


@rt(methods=["POST"])
def update_password(token: str, new_password: str, confirm_password: str) -> HTMLResult:
    if new_password != confirm_password:
        return Alert(
            "Password Reset Failed", "Passwords do not match.", variant="error"
        )
    try:
        harbor.reset_password(new_password=new_password, reset_token=token)
    except UserHarborError as e:
        return Alert("Password Reset Failed", str(e), variant="error")
    return SuccessfulResetPasswordCard()
```

## List users with query-string pagination

Create the table component. Profile links contain URL-encoded usernames; HTML
text is escaped by FastHTML.

```python title="app/components/user_table.py"
from urllib.parse import quote

from fasthtml.common import FT, A, Tbody, Td, Th, Thead, Tr
from fasthtml_basecoat import Table
from userharbor.interfaces import UserList


def UserTable(users: UserList) -> FT:
    return Table(
        Thead(
            Tr(
                Th("Username"),
                Th("Email"),
                Th("Verified"),
            )
        ),
        Tbody(
            *[
                Tr(
                    Td(
                        A(
                            u.username,
                            href=f"/users/{quote(u.username, safe='')}",
                            cls="hover:underline",
                        )
                    ),
                    Td(u.email),
                    Td("Yes" if u.verified else "No"),
                )
                for u in users.items
            ]
        ),
    )
```

Use the installed Basecoat `Pagination` and `PaginationLink` wrappers. Links
such as `?page=2` work as normal URLs and inherit boosted navigation from the body.
The active page gets `aria-current="page"` from `PaginationLink(current=True)`.

```python title="app/components/pagination.py"
from fasthtml.common import FT
from fasthtml_basecoat import Pagination as BasePagination
from fasthtml_basecoat import PaginationLink


def Pagination(page: int, total_pages: int) -> FT | None:
    return (
        BasePagination(
            PaginationLink("Previous", href=f"?page={page - 1}") if page > 1 else None,
            *(
                PaginationLink(
                    str(number), href=f"?page={number}", current=number == page
                )
                for number in range(1, total_pages + 1)
            ),
            PaginationLink("Next", href=f"?page={page + 1}")
            if page < total_pages
            else None,
        )
        if total_pages > 1
        else None
    )
```

Compose them into a page using `DashboardLayout`. The `user` argument is the
signed-in viewer, used by the header.

```python title="app/pages/users.py"
from components.pagination import Pagination
from components.user_table import UserTable
from core.types import User
from fasthtml.common import FT
from layouts.dashboard import DashboardLayout
from userharbor.interfaces import UserList


def UsersPage(users: UserList, user: User, page: int, total_pages: int) -> FT:
    return DashboardLayout(
        UserTable(users),
        Pagination(page, total_pages),
        title="Users",
        user=user,
    )
```

Create the users router. FastHTML parses `page: int = 1` from the query string.
`harbor.users.list()` accepts `limit` and `offset`, and returns both the items
and the total number of matching users. That total determines the page count.

Clamp page numbers to the available range. An empty database still renders the
first page with an empty table. The details handler will be added in the next step.

```python title="app/routes/users.py"
from core.harbor import harbor
from core.types import HTMLResult
from fasthtml.common import HTTPException, fast_app
from pages.user_details import UserDetailsPage
from pages.users import UsersPage

users_app, rt = fast_app()


@rt(methods=["GET"])
def index(request, page: int = 1) -> HTMLResult:
    page_size = 10
    page = max(1, page)
    users = harbor.users.list(limit=page_size, offset=(page - 1) * page_size)
    total_pages = max(1, (users.total + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
        users = harbor.users.list(limit=page_size, offset=(page - 1) * page_size)
    return UsersPage(users, request.scope.get("user"), page, total_pages)
```

See [User Manager](../user-manager.md) for searching and sorting as well.

## Show user details and account forms

The details card displays the public user fields. The password form requires the
old password and two matching copies of the new password. The deletion form
requires the current password and explicit confirmation.

The checkbox enables the delete button only after confirmation. It lives in a
separate container because Basecoat disables pointer events on labels directly
followed by disabled controls. The server will check confirmation again; the
checkbox and disabled button are only browser-side interaction rules.

```python title="app/components/user_details.py"
from fasthtml.common import FT, H2, Div, Form, Header, P, Section, Tbody, Td, Tr
from fasthtml_basecoat import Button, Card, Checkbox, Input, Label, Table
from userharbor.interfaces import UserLike


def UserDetailsCard(user: UserLike) -> FT:
    return Card(
        Header(H2("User details")),
        Section(
            Table(
                Tbody(
                    Tr(
                        Td("Username", cls="font-semibold"),
                        Td(user.username),
                    ),
                    Tr(
                        Td("Email", cls="font-semibold"),
                        Td(user.email),
                    ),
                    Tr(
                        Td("Verified", cls="font-semibold"),
                        Td("Yes" if user.verified else "No"),
                    ),
                ),
            ),
        ),
    )


def ChangePasswordCard() -> FT:
    return Card(
        Header(
            H2("Change password"),
            P("You will need to log in again after changing your password."),
        ),
        Section(
            Form(
                Div(
                    Label("Current password", fr="old-password"),
                    Input(
                        type="password",
                        id="old-password",
                        name="old_password",
                        autocomplete="current-password",
                        required=True,
                    ),
                    cls="grid gap-2",
                ),
                Div(
                    Label("New password", fr="new-password"),
                    Input(
                        type="password",
                        id="new-password",
                        name="new_password",
                        autocomplete="new-password",
                        required=True,
                    ),
                    cls="grid gap-2",
                ),
                Div(
                    Label("Confirm password", fr="confirm-password"),
                    Input(
                        type="password",
                        id="confirm-password",
                        name="confirm_password",
                        autocomplete="new-password",
                        required=True,
                    ),
                    cls="grid gap-2",
                ),
                Button("Change password", type="submit"),
                id="change-password-form",
                hx_post="/account/change_password",
                hx_disabled_elt="#change-password-form input, #change-password-form button",
                hx_swap="none",
                cls="grid gap-6",
            ),
        ),
    )


def DeleteAccountCard() -> FT:
    return Card(
        Header(H2("Delete account"), P("Deleting your account is permanent.")),
        Section(
            Form(
                Div(
                    Label("Current password", fr="delete-password"),
                    Input(
                        type="password",
                        id="delete-password",
                        name="password",
                        autocomplete="current-password",
                        required=True,
                    ),
                    cls="grid gap-2",
                ),
                Div(
                    Label(
                        Checkbox(
                            name="confirmed",
                            value="true",
                            required=True,
                            onchange="this.form.querySelector('button[type=submit]').disabled = !this.checked",
                        ),
                        "I understand that my account will be permanently deleted.",
                        cls="flex items-center gap-2",
                    ),
                ),
                Button(
                    "Delete account",
                    type="submit",
                    variant="destructive",
                    disabled=True,
                ),
                id="delete-account-form",
                hx_post="/account/delete",
                hx_disabled_elt="#delete-account-form input, #delete-account-form button",
                hx_swap="none",
                cls="grid gap-6",
            ),
        ),
    )
```

Create the details page. Compare the stored username with the authenticated
viewer's username. Only an owner sees the two account forms. Looking up another
user never changes which account the session represents.

```python title="app/pages/user_details.py"
from components.user_details import (
    ChangePasswordCard,
    DeleteAccountCard,
    UserDetailsCard,
)
from core.types import User
from fasthtml.common import FT
from layouts.dashboard import DashboardLayout
from userharbor.interfaces import UserLike


def UserDetailsPage(profile: UserLike, user: User) -> FT:
    is_owner = profile.username == user.username
    return DashboardLayout(
        UserDetailsCard(profile),
        (ChangePasswordCard(), DeleteAccountCard()) if is_owner else None,
        title=profile.username,
        user=user,
    )
```

Append the lookup handler to `app/routes/users.py`. The username comes from the
URL path. `get_by_username()` returns `None` for a missing account; return 404 in
that case. The lookup is case-insensitive and preserves the stored username.

For this demonstration, every signed-in user can read the user directory and
profiles. User Manager reads do not enforce permissions. Apply your application's
access rules here if those pages should have a narrower audience.

```python title="app/routes/users.py"
@rt("/users/{username}", methods=["GET"])
def details(request, username: str) -> HTMLResult:
    profile = harbor.users.get_by_username(username)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserDetailsPage(profile, request.scope["user"])
```

## Change passwords and delete the signed-in account

Create a separate mounted router at `/account`. These operations take their
identity from the session cookie, not from a submitted username or the profile URL.
UserHarbor validates the token and current password before changing the account.

On a successful password change, all sessions are invalidated. Both successful
operations clear the browser cookie and redirect to login. Errors return the
same out-of-band alert used by the authentication forms.

The deletion handler also checks `confirmed` on the server. Hiding a form or
disabling a button alone is not authorization.

```python title="app/routes/account.py"
from components.alert import Alert
from core.harbor import harbor
from core.types import HTMLResult
from fasthtml.common import Response, fast_app
from userharbor.exceptions import UserHarborError

account_app, rt = fast_app()


@rt(methods=["POST"])
def change_password(
    request, old_password: str, new_password: str, confirm_password: str
) -> HTMLResult:
    if new_password != confirm_password:
        return Alert(
            "Password Change Failed", "Passwords do not match.", variant="error"
        )
    try:
        harbor.change_password(
            old_password=old_password,
            new_password=new_password,
            session_token=request.cookies.get("session_token", ""),
        )
    except UserHarborError as e:
        return Alert("Password Change Failed", str(e), variant="error")
    response = Response(headers={"HX-Redirect": "/auth/"})
    response.delete_cookie("session_token", path="/")
    return response


@rt(methods=["POST"])
def delete(request, password: str, confirmed: bool = False) -> HTMLResult:
    if not confirmed:
        return Alert(
            "Account Deletion Failed",
            "Confirm account deletion first.",
            variant="error",
        )
    try:
        harbor.delete_account(
            password=password,
            session_token=request.cookies.get("session_token", ""),
        )
    except UserHarborError as e:
        return Alert("Account Deletion Failed", str(e), variant="error")
    response = Response(headers={"HX-Redirect": "/auth/"})
    response.delete_cookie("session_token", path="/")
    return response
```

## Protect pages and mount the routers

Create `app/main.py`. The root middleware validates the session before dispatching
to any mounted application and puts the current user in `request.scope["user"]`.
A hook on just one child FastHTML application would not protect its siblings.

Authentication pages and static assets remain accessible without a session.
Authenticated users are sent away from the login screen, while logout and email
verification/recovery links remain available.

Ordinary requests use a 303 redirect. For HTMX requests, the middleware returns
`HX-Redirect` with HTTP 200 so an expired session navigates to the login page
instead of inserting it into an existing form or alert target.

```python title="app/main.py"
from contextlib import suppress

from core.harbor import harbor
from fasthtml.common import FastHTML, Response, StaticImmutable
from routes.account import account_app
from routes.auth import auth_app
from routes.users import users_app
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette.routing import Mount
from userharbor.exceptions import UserHarborError


def redirect(request, url: str):
    if request.headers.get("HX-Request") == "true":
        return Response(headers={"HX-Redirect": url})
    return RedirectResponse(url, status_code=303)


async def check_session(request, call_next):
    path = request.url.path
    user = None
    if token := request.cookies.get("session_token"):
        with suppress(UserHarborError):
            user = harbor.get_current_user(token)
    request.scope["user"] = user

    public = path == "/auth" or path.startswith(("/auth/", "/static/"))
    if user and path in ("/auth", "/auth/", "/auth/login", "/auth/register"):
        return redirect(request, "/")
    if not user and not public:
        response = redirect(request, "/auth/")
        response.delete_cookie("session_token", path="/")
        return response
    return await call_next(request)


app = FastHTML(
    middleware=[Middleware(BaseHTTPMiddleware, dispatch=check_session)],
    routes=[
        Mount("/static", StaticImmutable(directory="static"), name="static"),
        Mount("/auth", auth_app, name="auth"),
        Mount("/account", account_app, name="account"),
        Mount("/", users_app, name="index"),
    ],
)
```

## Run the application

From the project root, start the application with the environment file:

```bash
cd app
uv run --env-file ../.env uvicorn main:app --reload
```

Open <http://localhost:8000>. Running from `app/` also makes the `core`, `routes`,
`pages`, and `components` imports resolve and places `users.db` beside `main.py`.

Try the complete flow:

1. Register an account and follow the verification link sent by email.
2. Log in and open your profile from the header or user table.
3. Create enough accounts to navigate to `?page=2` and back.
4. View another user's profile: the password and deletion forms are absent.
5. Change your password and log in again with the new one.
6. Log out, request a reset email, and set a new password through its link.
7. On your own profile, confirm deletion and enter your password to remove the account.

While a request is running, the shared spinner appears and that form's controls
are disabled. If a domain operation fails, an alert appears without replacing
the form. The logout button disables only itself.

## How the HTMX pieces fit together

| Attribute or header | Purpose in this application |
| --- | --- |
| `hx-boost` | Navigate internal links through HTML requests and update browser history. |
| `hx-post` | Submit form values to a FastHTML route. |
| `hx-swap="none"` | Leave the form in place unless the response explicitly replaces it. |
| `hx-swap-oob` | Append feedback to the shared alerts container. |
| `HX-Retarget` and `HX-Reswap` | Replace a card after a successful operation. |
| `HX-Redirect` | Navigate to a new page after login, logout, or account changes. |
| `hx-disabled-elt` | Disable selected form controls or the triggering button during a request. |
| `hx-indicator` | Show the shared loading indicator during a request. |

These attributes describe browser behavior directly beside the UI that triggers
it. The routes keep returning HTML; UserHarbor remains independent of HTMX and
FastHTML. See the HTMX documentation for
[boosted navigation](https://htmx.org/attributes/hx-boost/),
[disabled controls](https://htmx.org/attributes/hx-disabled-elt/), and
[redirect responses](https://htmx.org/headers/hx-redirect/).

## Continue with the starter

The [FastHTML Starter repository](https://github.com/userharbor/fasthtml-starter)
contains the complete application shown in the presentation, including the
responsive dashboard sidebar and navigation components. Its structure follows
the same settings → components → layouts → pages → routes separation used here.

Before deploying your own application, configure HTTPS and secure cookies,
protect cookie-authenticated state-changing routes against CSRF, keep secrets
outside version control, and decide who may view the user directory. Use your
normal deployment process for database migrations, SMTP delivery, and rate limits.

For a deeper explanation of this architecture, read
[Hypermedia Systems](https://hypermedia.systems/), the free book from the creators
of [HTMX](https://github.com/bigskysoftware/htmx).

