"""Tests for SlotSync. Run with: pytest -v"""

from datetime import date, timedelta

import pytest

import store
from app import app

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
FAR_FUTURE = (date.today() + timedelta(days=30)).isoformat()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    store.reset()
    return app.test_client()


def form(**overrides):
    data = {
        "name": "Aarav Mehta",
        "prn": "1272250949",
        "facility": "Basketball Court",
        "slot": "18:00-19:00",
        "date": TODAY,
    }
    data.update(overrides)
    return data


def test_health_reports_ok_and_commit(client):
    body = client.get("/health").json
    assert body["status"] == "broken"
    assert body["commit"]


def test_booking_appears_on_page_and_in_api(client):
    assert client.post("/book", data=form()).status_code == 302
    page = client.get("/").data
    assert b"Aarav Mehta" in page
    assert b"Basketball Court" in page
    rows = client.get("/api/bookings").json
    assert len(rows) == 1
    assert rows[0]["slot"] == "18:00-19:00"


def test_double_booking_same_facility_is_rejected(client):
    client.post("/book", data=form())
    clash = client.post("/book", data=form(name="Neha Rao", prn="1272250777"))
    assert clash.status_code == 409
    assert len(client.get("/api/bookings").json) == 1


def test_same_facility_different_slot_is_allowed(client):
    client.post("/book", data=form())
    second = client.post("/book", data=form(slot="19:00-20:00", prn="1272250777"))
    assert second.status_code == 302
    assert len(client.get("/api/bookings").json) == 2


def test_invalid_input_is_rejected(client):
    assert client.post("/book", data=form(name="")).status_code == 400
    assert client.post("/book", data=form(prn="abc")).status_code == 400
    assert client.post("/book", data=form(slot="03:00-04:00")).status_code == 400
    assert client.post("/book", data=form(facility="Swimming Pool")).status_code == 400
    assert client.post("/book", data=form(date=YESTERDAY)).status_code == 400
    assert client.post("/book", data=form(date=FAR_FUTURE)).status_code == 400
    assert client.get("/api/bookings").json == []


def test_availability_shrinks_then_recovers_after_cancel(client):
    total = store.TOTAL_SLOTS_PER_DAY
    client.post("/book", data=form())
    after_booking = client.get("/api/availability?date=%s" % TODAY).json
    assert after_booking["seats_left"] == total - 1

    booking_id = client.get("/api/bookings").json[0]["id"]
    assert client.post("/cancel/%d" % booking_id).status_code == 302
    after_cancel = client.get("/api/availability?date=%s" % TODAY).json
    assert after_cancel["seats_left"] == total


def test_cancelling_unknown_booking_returns_404(client):
    assert client.post("/cancel/999").status_code == 404


def test_date_filter_only_shows_that_day(client):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post("/book", data=form())
    client.post("/book", data=form(name="Neha Rao", prn="1272250777", date=tomorrow))
    assert len(client.get("/api/bookings?date=%s" % TODAY).json) == 1
    assert len(client.get("/api/bookings").json) == 2
    assert b"Neha Rao" not in client.get("/?date=%s" % TODAY).data
