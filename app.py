"""SlotSync - campus sports slot booking portal.

Every page is rendered by the server from the in-memory booking store,
so the site is dynamic: posting the form changes what the next request
returns.
"""

import os
from datetime import date

from flask import Flask, jsonify, redirect, render_template, request

import store

app = Flask(__name__)

COMMIT = (os.getenv("GIT_SHA") or os.getenv("RENDER_GIT_COMMIT") or "local")[:7]


def _selected_date():
    """Date the user is looking at, defaulting to today."""
    raw = request.args.get("date", "").strip()
    return raw or date.today().isoformat()


@app.route("/")
def home():
    day = _selected_date()
    return render_template(
        "index.html",
        bookings=store.all_bookings(day),
        availability=store.availability(day),
        facilities=store.FACILITIES,
        slots=store.SLOTS,
        seats_left=store.seats_left(day),
        total_slots=store.TOTAL_SLOTS_PER_DAY,
        selected_date=day,
        today=date.today().isoformat(),
        commit=COMMIT,
    )


@app.route("/book", methods=["POST"])
def book():
    try:
        store.add(
            name=request.form.get("name"),
            prn=request.form.get("prn"),
            facility=request.form.get("facility"),
            day=request.form.get("date"),
            slot=request.form.get("slot"),
        )
    except store.BookingError as err:
        if request.form.get("as_json"):
            return jsonify({"error": err.message}), err.status
        return err.message, err.status
    return redirect("/?date=%s" % request.form.get("date", "").strip())


@app.route("/cancel/<int:booking_id>", methods=["POST"])
def cancel(booking_id):
    try:
        removed = store.cancel(booking_id)
    except store.BookingError as err:
        return err.message, err.status
    return redirect("/?date=%s" % removed["date"])


@app.route("/api/bookings")
def api_bookings():
    day = request.args.get("date", "").strip() or None
    return jsonify(store.all_bookings(day))


@app.route("/api/availability")
def api_availability():
    day = _selected_date()
    return jsonify(
        {
            "date": day,
            "seats_left": store.seats_left(day),
            "total_slots": store.TOTAL_SLOTS_PER_DAY,
            "facilities": store.availability(day),
        }
    )


@app.route("/health")
def health():
    return {"status": "ok", "commit": COMMIT, "bookings": store.count()}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
