---
title: Token Expiration
description: Configure token lifetimes and sliding session expiration.
icon: lucide/timer

---
# Token Expiration

UserHarbor stores expiration times for all tokens it creates. Expired tokens are
rejected and removed when UserHarbor encounters them.

## Default lifetimes

The default token lifetimes are:

* email verification tokens: 24 hours,
* password reset tokens: 1 hour,
* session tokens: 30 days.

These defaults are intentionally conservative and can be changed per
`UserHarbor` instance.

## Custom lifetimes

Pass custom `timedelta` values to `UserHarbor` when creating the instance:

```python
from datetime import timedelta

from userharbor import UserHarbor


harbor = UserHarbor(
    secret_key="your-secret-key",
    store=store,
    email_sender=email_sender,
    email_verification_token_ttl=timedelta(hours=12),
    password_reset_token_ttl=timedelta(minutes=30),
    session_token_ttl=timedelta(days=14),
)
```

`email_verification_token_ttl` is used when registering users and resending
verification emails.

`password_reset_token_ttl` is used when creating password reset tokens.

`session_token_ttl` is used when creating session tokens and when refreshing
active sessions.

## Sliding session expiration

Sessions use sliding expiration by default. When a valid session has less than
7 days left, UserHarbor refreshes its expiration to:

```text
now + session_token_ttl
```

Configure the refresh threshold with `session_refresh_threshold`:

```python
from datetime import timedelta

from userharbor import UserHarbor


harbor = UserHarbor(
    secret_key="your-secret-key",
    store=store,
    email_sender=email_sender,
    session_token_ttl=timedelta(days=30),
    session_refresh_threshold=timedelta(days=3),
)
```

Set `session_refresh_threshold=None` to disable session refresh:

```python
harbor = UserHarbor(
    secret_key="your-secret-key",
    store=store,
    email_sender=email_sender,
    session_refresh_threshold=None,
)
```

Storage adapters must persist refreshed session expiration times through
`UserStore.refresh_session()`.
