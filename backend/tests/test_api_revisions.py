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

    # 2. Non-hourly minute/second unaligned (:15) rejected
    r_minute = client.get("/api/revisions", params={"target_start_time": "2026-01-02T10:15:00Z"})
    assert r_minute.status_code == 400
    assert "hourly boundary" in r_minute.json()["detail"]

    # 3. Out of scope date prior to January 2 (2026-01-01) rejected
    r_early = client.get("/api/revisions", params={"target_start_time": "2026-01-01T23:00:00Z"})
    assert r_early.status_code == 400
    assert "out of scope" in r_early.json()["detail"]

    # 4. Out of scope date after February 1 (March 2026) rejected
    r_out = client.get("/api/revisions", params={"target_start_time": "2026-03-01T10:00:00Z"})
    assert r_out.status_code == 400
    assert "out of scope" in r_out.json()["detail"]


def test_target_start_time_timezone_contract(client):
    """
    Contract verification for validate_target_start_time():
    - Accepts 'Z' UTC timestamp
    - Accepts explicit UTC offset and converts correctly
    - Rejects timezone-naive timestamp with HTTP 400
    """
    # 1. Valid 'Z' timestamp
    r_z = client.get("/api/revisions", params={"target_start_time": "2026-01-02T10:00:00Z"})
    assert r_z.status_code == 200
    assert r_z.json()["target_start_time"] == "2026-01-02T10:00:00Z"

    # 2. Valid explicit offset: +01:00 (11:00+01:00 == 10:00 UTC)
    r_offset = client.get("/api/revisions", params={"target_start_time": "2026-01-02T11:00:00+01:00"})
    assert r_offset.status_code == 200
    assert r_offset.json()["target_start_time"] == "2026-01-02T10:00:00Z"

    # 3. Timezone-naive timestamp rejected with HTTP 400
    r_naive = client.get("/api/revisions", params={"target_start_time": "2026-01-02T10:00:00"})
    assert r_naive.status_code == 400
    assert "Timezone offset or 'Z' is required" in r_naive.json()["detail"]
