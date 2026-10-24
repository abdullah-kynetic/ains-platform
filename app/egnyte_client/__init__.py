"""Egnyte API client for Kien Solutions.

See ``client.py`` for the doc URLs each call is built against. CLI:
``uv run python -m app.egnyte_client --help``.
"""

from .client import (
    DEFAULT_SCOPES,
    MAX_REQUESTS_PER_SECOND,
    SIMPLE_UPLOAD_MAX_BYTES,
    EgnyteClient,
    FileEntry,
    FolderEntry,
    FolderListing,
    TokenSet,
    normalize_domain,
)
from .errors import (
    EgnyteAPIError,
    EgnyteAuthError,
    EgnyteConfigError,
    EgnyteError,
    EgnyteNotFoundError,
    EgnytePermissionError,
    EgnyteRateLimitError,
)
from .paths import DEFAULT_DEV_ROOT, PathNotAllowedError, encode_path, guard_path

__all__ = [
    "DEFAULT_DEV_ROOT",
    "DEFAULT_SCOPES",
    "MAX_REQUESTS_PER_SECOND",
    "SIMPLE_UPLOAD_MAX_BYTES",
    "EgnyteAPIError",
    "EgnyteAuthError",
    "EgnyteClient",
    "EgnyteConfigError",
    "EgnyteError",
    "EgnyteNotFoundError",
    "EgnytePermissionError",
    "EgnyteRateLimitError",
    "FileEntry",
    "FolderEntry",
    "FolderListing",
    "PathNotAllowedError",
    "TokenSet",
    "encode_path",
    "guard_path",
    "normalize_domain",
]
