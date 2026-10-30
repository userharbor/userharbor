"""Reusable contract tests for ``UserStore`` implementations.

Import all tests from this package into a test module in an adapter package and
provide a function-scoped ``user_store`` fixture:

    from userharbor.testing.user_store_contract import *
"""

from .email_verifications import *
from .password_resets import *
from .permissions import *
from .roles import *
from .sessions import *
from .transactions import *
from .user_listing import *
from .users import *

__all__ = [name for name in globals() if name.startswith("test_")]
