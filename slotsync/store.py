"""In-memory booking store and validation rules for SlotSync.

Kept separate from the Flask routes so the booking rules can be tested
on their own and so app.py stays readable.
"""

from datetime import date, datetime, timedelta

FACILITIES = [
    "Basketball Court",
    "Badminton Court A",
    "Badminton Court B",
    "Table Tennis Room",
]

SLOTS = [
    "06:00-07:00",
    "07:00-08:00",
    "17:00-18:00",
    "18:00-19:00",
    "19:00-20:00",
]

BOOKING_WINDOW_DAYS = 7
TOTAL_SLOTS_PER_DAY = len(FACILITIES) * len(SLOTS)

_bookings = []
_next_id = 1


class BookingError(Exception):
    """Raised when a booking request breaks a validation or conflict rule."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def reset():
    """Clear every booking. Used by the tests and by the seed helper."""
    global _bookings, _next_id
    _bookings = []
    _next_id = 1


def all_bookings(day=None):
    """Return bookings, newest first, optionally filtered to one date."""
    rows = _bookings if day is None else [b for b in _bookings if b["date"] == day]
    return sorted(rows, key=lambda b: (b["date"], b["slot"], b["facility"]))


def count():
    return len(_bookings)


def seats_left(day):
    return TOTAL_SLOTS_PER_DAY - len(all_bookings(day))


def availability(day):
    """Per-facility view of which slots are still open on a given date."""
    taken = {(b["facility"], b["slot"]) for b in all_bookings(day)}
    return [
        {
            "facility": facility,
            "open": [s for s in SLOTS if (facility, s) not in taken],
            "booked": [s for s in SLOTS if (facility, s) in taken],
        }
        for facility in FACILITIES
    ]


def _clean_date(raw):
    try:
        parsed = datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        raise BookingError("Date must be in YYYY-MM-DD format")
    today = date.today()
    if parsed < today:
        raise BookingError("Cannot book a slot in the past")
    if parsed > today + timedelta(days=BOOKING_WINDOW_DAYS):
        raise BookingError(
            "Bookings open only %d days in advance" % BOOKING_WINDOW_DAYS
        )
    return parsed.isoformat()


def add(name, prn, facility, day, slot):
    """Validate a request and store it. Raises BookingError on any problem."""
    global _next_id

    name = (name or "").strip()
    prn = (prn or "").strip()
    facility = (facility or "").strip()
    slot = (slot or "").strip()

    if not 2 <= len(name) <= 40:
        raise BookingError("Name must be between 2 and 40 characters")
    if not (prn.isdigit() and 8 <= len(prn) <= 12):
        raise BookingError("PRN must be 8 to 12 digits")
    if facility not in FACILITIES:
        raise BookingError("Unknown facility")
    if slot not in SLOTS:
        raise BookingError("Unknown time slot")

    day = _clean_date(day)

    for existing in _bookings:
        if (existing["facility"], existing["date"], existing["slot"]) == (
            facility,
            day,
            slot,
        ):
            raise BookingError(
                "%s is already booked for %s on %s" % (facility, slot, day),
                status=409,
            )
        if (existing["prn"], existing["date"], existing["slot"]) == (prn, day, slot):
            raise BookingError(
                "PRN %s already has a slot at %s on %s" % (prn, slot, day),
                status=409,
            )

    booking = {
        "id": _next_id,
        "name": name,
        "prn": prn,
        "facility": facility,
        "date": day,
        "slot": slot,
    }
    _bookings.append(booking)
    _next_id += 1
    return booking


def cancel(booking_id):
    """Remove a booking by id and free the slot. Returns the removed row."""
    for index, booking in enumerate(_bookings):
        if booking["id"] == booking_id:
            return _bookings.pop(index)
    raise BookingError("No booking with id %s" % booking_id, status=404)
