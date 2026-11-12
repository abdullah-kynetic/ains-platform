"""Independent review of PR #142: the one-run-at-a-time guard under concurrency. Synthetic only."""

import threading

import pytest
from fastapi import HTTPException

from app.api.ai_analysis import _RUNNING, _one_run_at_a_time
from app.database.models import Engagement
from tests.test_ai_analysis import BODY_MARK, ai, url  # noqa: F401
from tests.test_backend_api import backend, sign_in_auditor  # noqa: F401


def test_guard_admits_exactly_one_of_many_parallel_runs():
    inside = threading.Barrier(1)
    admitted, refused = [], []
    hold, started = threading.Event(), threading.Event()

    def attempt():
        try:
            with _one_run_at_a_time("eng-race"):
                admitted.append(1)
                started.set()
                assert hold.wait(10)
        except HTTPException as exc:
            refused.append(exc.status_code)

    first = threading.Thread(target=attempt)
    first.start()
    assert started.wait(10)
    rest = [threading.Thread(target=attempt) for _ in range(30)]
    for t in rest:
        t.start()
    for t in rest:
        t.join(10)
    hold.set()
    first.join(10)
    assert inside and len(admitted) == 1 and refused == [409] * 30
    assert "eng-race" not in _RUNNING


def test_guard_is_per_engagement_and_released_after_an_error():
    with _one_run_at_a_time("eng-a"), _one_run_at_a_time("eng-b"):
        pass  # two engagements never block each other
    with pytest.raises(RuntimeError), _one_run_at_a_time("eng-a"):
        raise RuntimeError("model blew up")
    with _one_run_at_a_time("eng-a"):  # lock was released by the failure
        pass
    assert not _RUNNING


def test_unexpected_model_crash_does_not_leave_the_engagement_locked(ai):  # noqa: F811
    client, _, ids, model, add_document, *_ = ai
    add_document("alerts.txt", BODY_MARK.encode())
    sign_in_auditor(client)
    original = model.analyze

    def crash(req, model_id):
        raise ValueError("boom")

    model.analyze = crash  # type: ignore[method-assign]
    with pytest.raises(ValueError):
        client.post(url(ids, "/run"))
    model.analyze = original  # type: ignore[method-assign]
    assert client.post(url(ids, "/run")).status_code == 200  # not stuck on 409


def test_run_in_flight_never_turns_a_denied_caller_into_a_409(ai):  # noqa: F811
    client, factory, ids, model, add_document, *_ = ai
    add_document("alerts.txt", BODY_MARK.encode())
    sign_in_auditor(client)
    entered, release = threading.Event(), threading.Event()
    original = model.analyze

    def slow(req, model_id):
        entered.set()
        assert release.wait(10)
        return original(req, model_id)

    model.analyze = slow  # type: ignore[method-assign]
    worker = threading.Thread(target=lambda: client.post(url(ids, "/run")))
    worker.start()
    assert entered.wait(10)
    with factory() as db:  # the auditor loses the assignment while a run is in flight
        db.get(Engagement, ids["engagement_a"]).auditor_id = None
        db.commit()
    denied = client.post(url(ids, "/run"))
    release.set()
    worker.join(10)
    assert denied.status_code == 404  # scope check comes first; 409 would confirm a hidden run
