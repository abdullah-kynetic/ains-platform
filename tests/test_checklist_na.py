"""Synthetic reversible NA, client privacy, assignment and tenant checks."""
from sqlalchemy import select

from app.checklist import ClientStatus
from app.database.models import AuditLog, ChecklistItemInstance, Engagement
from tests.test_backend_api import backend as backend
from tests.test_backend_api import sign_in_auditor, sign_in_client


def test_na_moves_to_bottom_counts_resolved_and_undo_restores(backend):
    client, factory, ids, _, _ = backend
    sign_in_auditor(client)
    path = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_a']}/na"
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids['item_a'])
        item.status = ClientStatus.ACTION_NEEDED_MORE
        item.assessment = "partial"
        item.client_reason = "Please provide missing pages."
        db.commit()
    response = client.post(path, json={"not_applicable": True})
    assert response.status_code == 200
    assert response.json()["readiness"]["reviewed"] == 1
    assert client.post(path, json={"not_applicable": True}).status_code == 200
    sign_in_client(client)
    response = client.get('/engagements/current').json()
    assert response['collectionProgress'] == {'total': 1, 'done': 1}
    items = [i for s in response['sections'] for i in s['items']]
    assert next(i for i in items if i['id'] == ids['item_a'])['status'] == 'not_applicable'
    assert client.post(path, json={"not_applicable": False}).status_code == 403
    sign_in_auditor(client)
    assert client.post(path, json={"not_applicable": False}).status_code == 200
    with factory() as db:
        item = db.get(ChecklistItemInstance, ids['item_a'])
        assert item.status == ClientStatus.ACTION_NEEDED_MORE
        assert item.assessment == 'partial'
        assert item.client_reason == 'Please provide missing pages.'
        assert item.na_previous_state is None
        assert [e.action for e in db.scalars(select(AuditLog).where(
            AuditLog.action.in_(['request.na_set', 'request.na_unset'])
        )).all()] == ['request.na_set', 'request.na_set', 'request.na_unset']


def test_na_rejects_mismatched_firm_and_unassigned_auditor(backend):
    client, factory, ids, _, _ = backend
    sign_in_auditor(client)
    bad = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_b']}/na"
    assert client.post(bad, json={"not_applicable": True}).status_code == 404
    with factory() as db:
        db.get(Engagement, ids['engagement_a']).auditor_id = ids['enrolling_auditor']
        db.commit()
    path = f"/auditor/engagements/{ids['engagement_a']}/items/{ids['item_a']}/na"
    for value in [True, False]:
        assert client.post(path, json={"not_applicable": value}).status_code == 404
    sign_in_client(client, 'beta-client@example.test')
    assert client.post(path, json={"not_applicable": True}).status_code == 403
