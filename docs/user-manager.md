---
title: User Manager
description: Look up and list users to build application-specific management tools.
icon: lucide/users

---
# User Manager

`harbor.users` provides user lookup, search, sorting, and pagination through a
framework-independent API. You can use it to build a user management panel,
support dashboard, or internal CLI tool.

The manager gives you the building blocks while leaving the concrete
implementation to your application. Your business requirements determine the
interface, who can access it, which user data is visible, and which actions are
available. You can combine these reads with existing account and
[role and permission operations](roles-and-permissions.md) to create the
workflow you need.

The examples below use an already configured `UserHarbor` instance named
`harbor`.

## Looking up a user

Find an account by username or email:

```python
user = harbor.users.get_by_username("alice")
user = harbor.users.get_by_email("alice@example.com")

if user is not None:
    print(user.username, user.email, user.verified)
```

Both methods return `UserT | None`: the public user object, or `None` when the
account does not exist. Username lookup is case-insensitive and preserves the
stored username casing. Email lookup normalizes the supplied address to
lowercase, as registration does.

## Listing and searching users

```python
users = harbor.users.list(
    limit=25,
    offset=0,
    order="username",
    query="alice",
)

for user in users.items:
    print(user.username, user.email)

print(users.total)
```

The result is a `UserList[UserT]`, defined in `userharbor.interfaces`:

* `items` contains the users on the requested page.
* `total` counts all users matching the query before pagination. It remains
  available even when the requested page is empty.

`query` matches a literal substring of either the username or email, without
case sensitivity. Leading and trailing whitespace is ignored. `None`, an empty
string, or whitespace alone lists all users. Characters such as `%` and `_`
are treated as ordinary characters.

### Pagination

`limit` defaults to `50` and must be between `1` and `500`. `offset` defaults
to `0` and must not be negative. Invalid pagination arguments raise `ValueError`.

Use `total` to calculate the page count for your interface:

```python
page_size = 25
page_number = 2  # Pages in this example start at 1.

users = harbor.users.list(
    limit=page_size,
    offset=(page_number - 1) * page_size,
    query="alice",
)
page_count = (users.total + page_size - 1) // page_size
```

### Sorting

`order` defaults to `"username"`. Pass a storage field name for ascending order
or prefix it with `-` for descending order:

```python
users = harbor.users.list(order="email")
users = harbor.users.list(order="-verified")
```

Usernames are ordered using `casefold()`. Equal sort values are ordered by
username ascending to keep pagination deterministic for an unchanged dataset.

Field names are passed to the store without a list of allowed fields.
Unsupported names raise an error. With the SQLAlchemy adapter, `order` names
an attribute of the database model, so custom model fields can also be used:

```python
users = harbor.users.list(order="-display_name")
```

A field created only by `user_mapper` needs a corresponding sortable attribute
on the storage model; the manager does not translate public field names.

## Building a user management panel

User manager reads do not require a session or a verified account, and do not
check the caller's permissions. Apply your application's access rules before
calling them. For example, if your application has configured and assigned a
`users.read` permission:

```python
def list_users_for_admin(session_token, *, query=None, limit=25, offset=0):
    harbor.require_permission(session_token, "users.read")
    return harbor.users.list(
        limit=limit,
        offset=offset,
        order="username",
        query=query,
    )
```

Your UI can display `items` in a table and use `total` for pagination. The same
domain operation can serve a web view, an API route, or an internal tool. Choose
the presentation, access policy, and available management actions to fit your
business case.

## Custom user types

Lookups and listings preserve the public `UserT` returned by your store. With
the SQLAlchemy adapter, list items use the same `user_mapper` as individual
lookups, so custom public fields remain available to your application.

See [Custom user mapping](integrations/sqlalchemy.md#custom-user-mapping) for
an example.
