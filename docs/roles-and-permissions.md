---
title: Roles and Permissions
description: Configure role-based access control with UserHarbor.
icon: lucide/shield-check

---
# Roles and Permissions

UserHarbor includes simple role-based access control for applications that need
basic authorization without a framework-specific policy engine.

The core library manages:

* role definitions
* permission definitions
* permissions granted to roles
* roles granted to users
* role and permission checks for active sessions

UserHarbor does not decide how your application maps permissions to routes,
views, commands, or business objects. Framework adapters and application code
remain responsible for turning a denied permission into an HTTP response, CLI
error, or other application-specific result.

## Naming

Roles are short lowercase names:

```text
admin
support-agent
billing_manager
```

Permissions use dot-separated names:

```text
users.read
users.delete
billing.invoices.create
```

Permissions must contain at least one dot. This keeps permission names grouped
by domain and action from the beginning.

## Creating roles and permissions

Create roles through `harbor.roles` and permissions through
`harbor.permissions`:

```python
harbor.roles.create("admin")
harbor.permissions.create("users.delete")
```

List existing roles and permissions:

```python
roles = harbor.roles.list()
permissions = harbor.permissions.list()
```

Delete roles and permissions:

```python
harbor.roles.delete("admin")
harbor.permissions.delete("users.delete")
```

Deleting a role also removes that role from users and removes its permission
assignments. Deleting a permission removes it from every role.

## Granting permissions to roles

Grant permissions to roles:

```python
harbor.roles.grant_permission("admin", "users.delete")
```

Revoke permissions from roles:

```python
harbor.roles.revoke_permission("admin", "users.delete")
```

Inspect permissions assigned to a role:

```python
admin_permissions = harbor.roles.permissions("admin")
```

Grant and revoke operations are idempotent for the relationship itself. Granting
the same permission twice does not duplicate it, and revoking a permission that
is not currently assigned does not fail.

## Granting roles to users

Grant roles to users by username:

```python
harbor.grant_role("jane", "admin")
```

Revoke roles from users:

```python
harbor.revoke_role("jane", "admin")
```

Inspect a user's roles and effective permissions:

```python
roles = harbor.get_roles("jane")
permissions = harbor.get_permissions("jane")
```

Effective permissions are derived from all roles currently assigned to the user.

## Checking access

Use `has_role()` and `has_permission()` when your application wants to branch on
authorization:

```python
if harbor.has_permission(session_token, "users.delete"):
    delete_user()
```

These methods return `True` or `False`. They return `False` when the session is
invalid or when the authenticated user does not have the requested role or
permission.

Invalid role or permission names are rejected. Unknown roles and permissions are
also rejected, which helps catch typos during development.

Use `require_role()` and `require_permission()` when the operation must stop if
access is denied:

```python
current_user = harbor.require_permission(session_token, "users.delete")
```

`require_role()` and `require_permission()` return the current user when access
is allowed.

They raise:

* `InvalidSessionTokenError` when the session is missing, invalid, or expired
* `PermissionDeniedError` when the session is valid but the user does not have
  the requested role or permission

This distinction lets framework integrations map invalid sessions to `401
Unauthorized` and denied permissions to `403 Forbidden`.

## Store responsibility

Roles and permissions are part of the `UserStore` contract. Storage adapters are
responsible for persisting role definitions, permission definitions,
role-to-permission assignments, and user-to-role assignments.

The core library validates names and enforces high-level behavior. The store
owns persistence details such as tables, joins, constraints, and cascades.
