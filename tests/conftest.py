import pytest

from app.egnyte_client import EgnyteClient

BASE = "https://testfirm.egnyte.com"
CLIENT_ID = "cid-123456"
CLIENT_SECRET = "csecret-abcdef"
USERNAME = "ains-app"
PASSWORD = "pw-supersecret"
ACCESS = "access-tok-111111"
REFRESH = "refresh-tok-222222"


class SleepRecorder:
    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


@pytest.fixture
def sleeps() -> SleepRecorder:
    return SleepRecorder()


@pytest.fixture
def make_client(sleeps):
    created: list[EgnyteClient] = []

    def _make(**kw) -> EgnyteClient:
        args = dict(
            domain="testfirm",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            username=USERNAME,
            password=PASSWORD,
            sleep=sleeps,
            max_per_second=0,
        )
        args.update(kw)
        c = EgnyteClient(**args)
        created.append(c)
        return c

    return _make


def token_json(access: str = ACCESS, refresh: str | None = REFRESH) -> dict:
    body = {"access_token": access, "token_type": "bearer", "expires_in": 2592000}
    if refresh:
        body["refresh_token"] = refresh
    return body
