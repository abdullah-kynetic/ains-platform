"""S-07: collect existing behavioral rate-limit and lockout proofs in the security suite."""

from tests.test_rate_limit import (
    test_concurrent_uploads_are_capped_and_released as test_capped_upload_slots,
)
from tests.test_rate_limit import (
    test_rate_limit_per_client_with_retry_after_and_health_exempt as test_request_rate_limit,
)
from tests.test_signin_lockout import (
    test_lockout_after_repeated_failures_blocks_even_the_right_password as test_password_lockout,
)
from tests.test_signin_lockout import (
    test_other_accounts_are_not_locked_by_one_email as test_lockout_isolation,
)

__all__ = [
    "test_capped_upload_slots",
    "test_request_rate_limit",
    "test_password_lockout",
    "test_lockout_isolation",
]
