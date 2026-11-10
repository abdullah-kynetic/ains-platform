"""S-10: retain the existing fail-closed scanning and upload boundary proofs."""

from tests.test_document_ingestion import (
    test_ingestor_rejects_invalid_files_before_egnyte as test_invalid_uploads,
)
from tests.test_document_ingestion import (
    test_ingestor_rejects_oversized_file as test_oversized_upload,
)
from tests.test_route_isolation import (
    test_restricted_item_rejects_uploads_for_the_owning_client as test_restricted_upload,
)
from tests.test_upload_scanning import clamd as clamd
from tests.test_upload_scanning import (
    test_endpoint_blocks_stores_nothing_and_audits as test_endpoint_quarantine,
)
from tests.test_upload_scanning import (
    test_infected_file_is_quarantined_by_rejection_with_hash_only_audit as test_quarantine_metadata,
)
from tests.test_upload_scanning import (
    test_scanner_failure_fails_closed as test_scanner_fail_closed,
)

__all__ = [
    "test_invalid_uploads",
    "test_oversized_upload",
    "test_restricted_upload",
    "test_endpoint_quarantine",
    "test_quarantine_metadata",
    "test_scanner_fail_closed",
]
