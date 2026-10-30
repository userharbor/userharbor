import pytest

from userharbor.interfaces import UserStore

from ._support import create_user


def test_list_users_returns_empty_page(user_store: UserStore) -> None:
    page = user_store.list_users()

    assert page.items == []
    assert page.total == 0


def test_list_users_paginates_with_total_before_pagination(
    user_store: UserStore,
) -> None:
    for username in ("carol", "alice", "bob"):
        create_user(user_store, username=username, email=f"{username}@example.com")

    page = user_store.list_users(limit=1, offset=1)

    assert [user.username for user in page.items] == ["bob"]
    assert page.items[0].email == "bob@example.com"
    assert page.items[0].verified is False
    assert page.total == 3

    past_end = user_store.list_users(offset=3)
    assert past_end.items == []
    assert past_end.total == 3


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        ("username", ["alice", "Bob", "carol"]),
        ("-username", ["carol", "Bob", "alice"]),
        ("email", ["carol", "Bob", "alice"]),
        ("-email", ["alice", "Bob", "carol"]),
        ("verified", ["alice", "carol", "Bob"]),
        ("-verified", ["Bob", "alice", "carol"]),
    ],
)
def test_list_users_orders_with_username_tiebreaker(
    user_store: UserStore, order: str, expected: list[str]
) -> None:
    create_user(user_store, username="carol", email="a@example.com")
    create_user(user_store, username="Bob", email="b@example.com")
    create_user(user_store, username="alice", email="c@example.com")
    user_store.set_user_verified("Bob")

    page = user_store.list_users(order=order)

    assert [user.username for user in page.items] == expected
    assert page.total == 3


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (None, ["alice", "bob", "carol"]),
        ("", ["alice", "bob", "carol"]),
        ("   ", ["alice", "bob", "carol"]),
        (" LIC ", ["alice"]),
        ("SPECIAL", ["bob"]),
        ("example", ["alice", "bob"]),
        ("not-found", []),
    ],
)
def test_list_users_searches_username_or_email(
    user_store: UserStore, query: str | None, expected: list[str]
) -> None:
    create_user(user_store, username="alice", email="alice@example.com")
    create_user(user_store, username="bob", email="special@example.com")
    create_user(user_store, username="carol", email="carol@other.com")

    page = user_store.list_users(query=query)

    assert [user.username for user in page.items] == expected
    assert page.total == len(expected)


def test_list_users_searches_casefolded_username(user_store: UserStore) -> None:
    create_user(user_store, username="Straße")

    page = user_store.list_users(query="STRASSE")

    assert [user.username for user in page.items] == ["Straße"]


@pytest.mark.parametrize("query", ["%", "_", "/", "' OR 1=1 --"])
def test_list_users_search_treats_query_as_literal(
    user_store: UserStore, query: str
) -> None:
    create_user(user_store, username="alice", email=f"literal{query}@example.com")
    create_user(user_store, username="bob", email="bob@example.com")

    page = user_store.list_users(query=query)

    assert [user.username for user in page.items] == ["alice"]
    assert page.total == 1


def test_list_users_paginates_filtered_results(user_store: UserStore) -> None:
    create_user(user_store, username="carol", email="carol@other.com")
    create_user(user_store, username="bob", email="bob@example.com")
    create_user(user_store, username="alice", email="alice@example.com")

    page = user_store.list_users(query="example", order="-username", limit=1, offset=1)

    assert [user.username for user in page.items] == ["alice"]
    assert page.total == 2


def test_list_users_raises_for_unknown_order_field(user_store: UserStore) -> None:
    create_user(user_store)

    with pytest.raises((AttributeError, KeyError, ValueError)):
        user_store.list_users(order="missing_field")


__all__ = [name for name in globals() if name.startswith("test_")]
