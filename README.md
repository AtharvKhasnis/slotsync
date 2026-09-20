# SlotSync — Campus Sports Slot Booking

A dynamic Flask web application for booking campus sports facilities. Every page is
rendered by the server from live booking data, and the app is linted, tested,
containerised and deployed automatically by GitHub Actions.

**Live app:** `<your-render-url>`
**Actions:** `<your-repo-url>/actions`

---

## Features

- Book a facility for a date and time slot through a validated form
- **Double-booking prevention** — one facility can hold only one booking per slot per
  date, and a PRN cannot hold two slots at the same time (both return HTTP 409)
- Live availability table showing open and taken slots per facility
- Date filter on the home page and on the JSON API
- Cancel a booking, which immediately frees the slot
- Running commit ID shown in the footer and in `/health`

### Validation rules

| Field | Rule |
| --- | --- |
| Name | 2–40 characters |
| PRN | 8–12 digits |
| Facility | Must be one of the four configured facilities |
| Slot | Must be one of the five configured time slots |
| Date | `YYYY-MM-DD`, not in the past, at most 7 days ahead |

---

## Routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/` | Home page — booking form, availability, bookings for the selected date |
| POST | `/book` | Create a booking (302 on success, 400 invalid, 409 clash) |
| POST | `/cancel/<id>` | Cancel a booking (302 on success, 404 unknown id) |
| GET | `/api/bookings` | JSON list of bookings, optional `?date=` filter |
| GET | `/api/availability` | JSON per-facility open/booked slots and seats left |
| GET | `/health` | `{"status": "ok", "commit": "...", "bookings": n}` |

---

## Project structure

```
slotsync/
├── .github/workflows/ci-cd.yml   CI/CD pipeline
├── templates/index.html          Server-rendered page
├── static/style.css              Styling
├── app.py                        Flask routes
├── store.py                      Booking rules and in-memory store
├── test_app.py                   pytest suite (8 tests)
├── Dockerfile
├── requirements.txt
├── .flake8
├── .dockerignore
└── .gitignore
```

`store.py` is kept separate from `app.py` so the booking rules (conflict detection,
validation, availability maths) can be tested independently of HTTP handling.

---

## Run locally

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

flake8 .                          # lint
pytest -v                         # tests
python app.py                     # http://localhost:5000
```

With Docker:

```bash
docker build -t slotsync .
docker run -p 5000:5000 slotsync
```

---

## CI/CD pipeline

```
 git push
    │
    ▼
┌─────────────────────┐   flake8 . ──► pytest -v
│  1. Lint and Test   │   runs on every push and pull request
└─────────┬───────────┘
          │ needs:
          ▼
┌─────────────────────┐   docker build ──► docker run ──► curl /health
│  2. Build + Smoke   │   verifies the image boots and serves the commit id
└─────────┬───────────┘
          │ needs:
          ▼
┌─────────────────────┐   POST Render deploy hook with &ref=<commit sha>
│  3. Deploy          │   push to main only
└─────────┬───────────┘
          ▼
   Live site footer shows the same commit id
```

If any stage fails, every later stage is skipped because each job declares
`needs:` on the one before it — a failing test can never reach the deploy step.

### Pipeline jobs

| Job | Trigger | What it proves |
| --- | --- | --- |
| `lint-and-test` | Every push and PR | Style is clean and all 8 tests pass |
| `build` | After tests pass | The Docker image builds, boots, and `/health` answers with the right commit |
| `deploy` | Push to `main` only | Render releases exactly the commit that passed |

The deploy hook URL is never in the repository — it is stored as the GitHub secret
`RENDER_DEPLOY_HOOK`.

---

## Tests

| Test | Checks |
| --- | --- |
| `test_health_reports_ok_and_commit` | `/health` returns ok and a commit id |
| `test_booking_appears_on_page_and_in_api` | Form POST changes the rendered page and the API |
| `test_double_booking_same_facility_is_rejected` | Clash returns 409 and is not stored |
| `test_same_facility_different_slot_is_allowed` | Conflict rule is not over-strict |
| `test_invalid_input_is_rejected` | Six bad inputs all return 400 |
| `test_availability_shrinks_then_recovers_after_cancel` | Seat maths and cancel work |
| `test_cancelling_unknown_booking_returns_404` | Unknown id handled |
| `test_date_filter_only_shows_that_day` | Date filtering on page and API |

---

## Deployment (Render)

| Setting | Value |
| --- | --- |
| Language | Docker |
| Health check path | `/health` |
| Auto-Deploy | **Off** — GitHub Actions triggers the deploy |

Render sets `RENDER_GIT_COMMIT` automatically; the app reads it (falling back to the
`GIT_SHA` build argument used by the Docker image) and prints the first 7 characters
in the footer.
  
## Notes

Bookings are held in memory, so a Render restart clears them. That is intentional for
this assessment — the focus is the pipeline, not persistence. Swapping `store.py` for a
SQLite or Postgres backend would not change any route or test signature.
       