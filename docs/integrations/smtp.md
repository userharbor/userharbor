---
title: SMTP Integration
description: Send UserHarbor account emails through SMTP.
icon: lucide/mail

---
# SMTP Integration

`userharbor-smtp` provides `SMTPEmailSender`, an `EmailSender` implementation
that sends verification, password-reset, and account security notification
messages through SMTP.

Repository:

```text
https://github.com/userharbor/userharbor-smtp
```

## Installation

```bash
pip install userharbor-smtp
```

You can also install it through the core package extra:

```bash
pip install "userharbor[smtp]"
```

## Basic usage

```python
from userharbor_smtp import SMTPEmailSender

email_sender = SMTPEmailSender(
    host="smtp.example.com",
    port=587,
    username="smtp-user",
    password="smtp-password",
    from_email="noreply@example.com",
    from_name="UserHarbor",
)
```

Pass the sender to `UserHarbor` as its `email_sender`. UserHarbor calls it when
it needs to send:

* email verification messages
* password reset messages
* email-verified notifications
* password-changed notifications
* account-deleted notifications

## Configuration

```python
SMTPEmailSender(
    host="smtp.example.com",
    from_email="noreply@example.com",
    port=587,
    username=None,
    password=None,
    from_name=None,
    template_dir=None,
    verification_subject="Verify your email",
    password_reset_subject="Reset your password",
    email_verified_subject="Email verified",
    password_changed_subject="Password changed",
    account_deleted_subject="Account deleted",
    use_starttls=True,
    use_ssl=False,
    timeout=10,
)
```

Use `use_starttls=True` for the common SMTP submission flow on port 587. Use
`use_ssl=True` for implicit TLS, commonly on port 465. When `use_ssl=True`,
STARTTLS is not started separately.

If both `username` and `password` are provided, the sender authenticates before
sending the message.

## Templates

By default, the package uses bundled HTML templates:

* `verification.html`
* `password_reset.html`
* `email_verified.html`
* `password_changed.html`
* `account_deleted.html`

To use custom templates, pass a directory containing files with the same names:

```python
email_sender = SMTPEmailSender(
    host="smtp.example.com",
    port=587,
    username="smtp-user",
    password="smtp-password",
    from_email="noreply@example.com",
    template_dir="templates/emails",
)
```

Each template receives:

* `username`
* `email`

Verification and password reset templates also receive `token`.

Example `templates/emails/verification.html`:

```html
<p>Hello {{ username }},</p>
<p>Use this token to verify {{ email }}:</p>
<p><strong>{{ token }}</strong></p>
```

Example `templates/emails/password_reset.html`:

```html
<p>Hello {{ username }},</p>
<p>Use this token to reset your password:</p>
<p><strong>{{ token }}</strong></p>
```

Example `templates/emails/password_changed.html`:

```html
<p>Hello {{ username }},</p>
<p>The password for {{ email }} was changed.</p>
```
