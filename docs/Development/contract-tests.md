---
title: Contract tests
description: Developing and running the shared UserStore contract tests locally.
icon: lucide/list-checks

---
# Contract tests

The reusable `UserStore` contract tests live in
`userharbor.testing.user_store_contract`. Storage adapters import the complete
suite and provide a function-scoped `user_store` fixture:

```python
# tests/test_user_store_contract.py

from userharbor.testing.user_store_contract import *  # noqa: F403
```

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

The fixture must return a clean store for every test and clean up any databases,
connections, containers, or other resources it creates. Contract tests only use
the public `UserStore` interface. Backend-specific behavior should remain in the
adapter's own tests.

The adapter must include `pytest` in its development dependencies. With uv:

```bash
uv add --dev pytest
```

## Contract organization

The contract is organized by `UserStore` responsibility:

```text
userharbor/testing/user_store_contract/
    __init__.py
    _support.py
    users.py
    user_listing.py
    email_verifications.py
    password_resets.py
    sessions.py
    roles.py
    permissions.py
    transactions.py
```

Add a new test function to the module that owns the behavior being tested. Every
function named `test_*` is exported by that module and re-exported by the package,
so adapter imports remain unchanged as the suite grows.

Use `_support.py` only for shared test data, factories, and assertions. Contract
tests should continue to interact with stores exclusively through the public
`UserStore` interface.

The user contract includes identifier semantics required by the core. Username
lookups and uniqueness use Unicode `casefold()` comparison, while the username
returned by the store preserves its original casing. Adapter-specific tests
should cover the database constraint, collation, functional index, or normalized
key used to provide that behavior.

Run a focused group from an adapter repository with `-k`, for example:

```bash
uv run --with-editable ../userharbor pytest \
  tests/test_user_store_contract.py -k session
```

## Developing a contract across local repositories

Changes to the contract often need to be tested in both the main UserHarbor
repository and an adapter repository before a new UserHarbor version is
published. Keep the repositories next to each other:

```text
Dev/
    userharbor/
    userharbor-sqlalchemy/
```

From the adapter repository, run pytest with the local UserHarbor checkout
installed as an editable dependency:

```bash
cd ~/Dev/userharbor-sqlalchemy
uv run --with-editable ../userharbor pytest
```

This overlays the local checkout for that command without changing the
adapter's `pyproject.toml` or `uv.lock`. Uncommitted changes under
`userharbor/src/` are immediately available to the adapter, so contributors can
develop a new contract test and the corresponding adapter behavior together.

To confirm which UserHarbor checkout is imported:

```bash
uv run --with-editable ../userharbor python -c \
  "import userharbor; print(userharbor.__file__)"
```

The printed path should point to the local `userharbor/src/userharbor`
directory.

Run the main repository tests separately:

```bash
cd ~/Dev/userharbor
uv run pytest
```

Before submitting changes, both the main suite and every affected adapter suite
should pass.

## Versioning the contract

Contract tests are distributed with `userharbor`. After a UserHarbor release
adds or changes the suite, adapter packages must require a UserHarbor version
that contains the compatible contract. Before that release exists, use the
local `--with-editable` workflow described above.

Changing an existing contract test changes the behavior expected from every
`UserStore` implementation. Treat such changes like public API compatibility
changes: document the new requirement, update all official adapters, and test
the minimum and latest supported UserHarbor versions where they differ.

When an adapter starts importing the contract for the first time, publish the
UserHarbor version containing the suite before publishing the adapter version
that depends on it.
