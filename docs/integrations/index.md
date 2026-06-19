# Integrations

--8<-- "README.md:integrations"

Install both official adapters through the core package extras:

```bash
pip install "userharbor[sqlalchemy,smtp]"
```

Or install only the adapter you need:

```bash
pip install userharbor-sqlalchemy
pip install userharbor-smtp
```

## When to use each adapter

Use `userharbor-sqlalchemy` when your application already uses SQLAlchemy or
when you want UserHarbor data stored in a relational database.

Use `userharbor-smtp` when your email provider exposes SMTP credentials and you
want a simple email sender without provider-specific SDKs.

Both adapters can be replaced with custom implementations as long as they match
the core protocols.
