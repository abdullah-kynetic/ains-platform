import pytest

from app.checklist import ClientStatus
from app.egnyte_client import EgnyteClient, PathNotAllowedError, guard_path

ROOT = "/Shared/AINS-Dev"


@pytest.mark.parametrize(
    "path",
    [
        "/Shared/AINS-Dev",
        "/Shared/AINS-Dev/",
        "/Shared/AINS-Dev/client-001/aml-manual.pdf",
        "/shared/ains-dev/Client-001",
        "/Shared/AINS-Dev/./a/b",
    ],
)
def test_allowed(path: str) -> None:
    assert guard_path(path, ROOT)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "Shared/AINS-Dev/x",
        "/Shared",
        "/Shared/AINS-Dev-Prod/x",
        "/Shared/AINS-DevX",
        "/Shared/AINS-Dev/../Clients/real.pdf",
        "/Shared/AINS-Dev/..",
        "/Private/user/AINS-Dev",
        "/Shared/AINS-Dev\\..\\Clients",
        "/Shared/AINS-Dev/x\x00",
    ],
)
def test_rejected(path: str) -> None:
    with pytest.raises(PathNotAllowedError):
        guard_path(path, ROOT)


def test_normalizes() -> None:
    assert guard_path("/Shared/AINS-Dev//a/./b/", ROOT) == "/Shared/AINS-Dev/a/b"


async def test_client_methods_enforce_guard() -> None:
    c = EgnyteClient("example", "k", "s", "u", "p", root=ROOT)
    with pytest.raises(PathNotAllowedError):
        await c.list_folder("/Shared/Clients")
    await c.aclose()


def test_repr_hides_secrets() -> None:
    c = EgnyteClient("example", "secret-key", "secret-sec", "u", "secret-pass")
    assert "secret" not in repr(c)


def test_statuses() -> None:
    assert {s.name for s in ClientStatus} == {
        "REQUESTED",
        "CHECKING",
        "ACTION_NEEDED_REUPLOAD",
        "ACTION_NEEDED_MORE",
        "WITH_AUDITOR",
        "ACCEPTED_FOR_TESTING",
        "RESTRICTED_DO_NOT_UPLOAD",
    }
