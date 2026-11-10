"""S-14: execute the existing all-route server-side role/session matrix."""

from tests.test_route_isolation import (
    test_client_role_is_denied_on_every_auditor_route as test_client_role_denial,
)
from tests.test_route_isolation import (
    test_every_non_public_route_requires_a_session as test_session_required,
)

__all__ = ["test_client_role_denial", "test_session_required"]
