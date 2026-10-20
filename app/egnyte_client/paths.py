"""Path guard and Egnyte path encoding.

Path encoding rule (each segment URL-encoded separately, slashes kept):
https://developers.egnyte.com/docs/read/File_System_Management_API_Documentation (Path Encoding)
"""

from __future__ import annotations

import posixpath
from urllib.parse import quote

DEFAULT_DEV_ROOT = "/Shared/AINS-Dev"


class PathNotAllowedError(ValueError):
    """Raised when a path falls outside the allowed Egnyte root."""


def guard_path(path: str, root: str = DEFAULT_DEV_ROOT) -> str:
    """Return the normalized ``path`` if it is ``root`` or inside it, else raise.

    Rejects relative paths, ``..`` traversal, backslashes, and NUL bytes.
    Comparison is case-insensitive because Egnyte paths are case-insensitive.
    """
    if not isinstance(path, str) or not path:
        raise PathNotAllowedError("Path must be a non-empty string")
    if "\x00" in path or "\\" in path:
        raise PathNotAllowedError(f"Illegal characters in path: {path!r}")
    if not path.startswith("/"):
        raise PathNotAllowedError(f"Path must be absolute: {path!r}")
    if ".." in path.split("/"):
        raise PathNotAllowedError(f"Path traversal not allowed: {path!r}")

    norm_root = posixpath.normpath(root).rstrip("/")
    norm_path = posixpath.normpath(path)
    if norm_path.startswith("//"):
        norm_path = "/" + norm_path.lstrip("/")

    p, r = norm_path.casefold(), norm_root.casefold()
    if p != r and not p.startswith(r + "/"):
        raise PathNotAllowedError(f"Path {path!r} is outside allowed root {norm_root!r}")
    return norm_path


def encode_path(path: str) -> str:
    """URL-encode each segment of an absolute path, leaving ``/`` separators intact.

    ``/Shared/example?path/$file.txt`` -> ``/Shared/example%3Fpath/%24file.txt``
    """
    return "/".join(quote(seg, safe="") for seg in path.split("/"))
