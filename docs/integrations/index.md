---
title: Integrations
description: Official adapters for storage, email delivery, and framework usage.
icon: lucide/plug

---
# Integrations

--8<-- "README.md:integrations"

Install the official adapters through the core package extras:

```bash
pip install "userharbor[sqlalchemy,smtp,fastapi]"
```

Or install only the adapter you need:

```bash
pip install userharbor-sqlalchemy
pip install userharbor-smtp
pip install userharbor-fastapi
```

The FastAPI adapter can also be installed through its dedicated core extra:

```bash
pip install "userharbor[fastapi]"
```

## When to use each adapter

Use `userharbor-sqlalchemy` when your application already uses SQLAlchemy or
when you want UserHarbor data stored in a relational database.

Use `userharbor-smtp` when your email provider exposes SMTP credentials and you
want a simple email sender without provider-specific SDKs.

Use `userharbor-fastapi` when your application uses FastAPI and you want
ready-to-use account routes, bearer-session authentication, and dependency
helpers for current users, roles, and permissions.

All adapters can be replaced with custom implementations as long as they match
the core protocols or compose a configured `UserHarbor` instance.

See [Custom integrations](custom.md) for guidance on building your own storage,
email, framework, or provider adapter.
