import pytest


def test_get_revisions_identifies_selected_eligible_and_excluded(client):
    """Verify revision classifications: selected, eligible_but_not_selected, and published_after_cutoff."""
    response = client.get(
        "/api/revisions",
        params={
            "target_start_time": "2026-01-02T10:00:00Z",
            "cutoff_time": "09:50",
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["target_start_time"] == "2026-01-02T10:00:00Z"
    assert data["delivery_date"] == "2026-01-02"
    assert data["decision_date"] == "2026-01-01"
    assert data["decision_cutoff"] == "2026-01-01T09:50:00Z"

    revisions = data["revisions"]
    assert len(revisions) == 3
    assert data["eligible_revisions_count"] == 2

    # Check the 3 revisions in mock data:
    # 1. 04:30 UTC -> eligible_but_not_selected
    r1 = revisions[0]
    assert "04:30" in r1["publish_time"]
    assert r1["is_eligible"] is True
    assert r1["is_selected"] is False
    assert r1["status_reason"] == "eligible_but_not_selected"

    # 2. 08:30 UTC -> selected (latest eligible before 09:50 cutoff)
    r2 = revisions[1]
    assert "08:30" in r2["publish_time"]
    assert r2["is_eligible"] is True
    assert r2["is_selected"] is True
    assert r2["status_reason"] == "selected"

    # 3. 14:30 UTC -> published_after_cutoff
    r3 = revisions[2]
    assert "14:30" in r3["publish_time"]
    assert r3["is_eligible"] is False
    assert r3["is_selected"] is False
    assert r3["status_reason"] == "published_after_cutoff"

    # Selected revision summary
    sel = data["selected_revision"]
    assert sel is not None
    assert sel["publish_time"] == r2["publish_time"]
    assert sel["forecast_generation_mw"] == r2["forecast_generation_mw"]


def test_get_revisions_rejects_unaligned_or_out_of_scope_target(client):
    """Hourly alignment and scope validation."""
    # 1. Half-hourly unaligned (:30) rejected
    r_unaligned = client.get("/api/revisions", params={"target_start_time": "2026-01-02T10:30:00Z"})
    assert r_unaligned.status_code == 400
    assert "hourly boundary" in r_unaligned.json()["detail"]

    # 2. Out of scope date (March 2026) rejected
    r_out = client.get("/api/revisions", params={"target_start_time": "2026-03-01T10:00:00Z"})
    assert r_out.status_code == 400
    assert "out of scope" in r_out.json()["detail"]
