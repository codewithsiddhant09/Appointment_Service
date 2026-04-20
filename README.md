# Appointment Booking System

Production-ready, slot-based appointment booking API built with **FastAPI** and **MongoDB**, featuring distributed locking via **Redis**.

## Architecture

```
app/
├── core/
│   ├── config.py          # Pydantic settings from .env
│   ├── database.py        # Motor (async MongoDB) connection + indexes
│   ├── exceptions.py      # Typed application exceptions
│   └── logging.py         # Structured logging
├── models/
│   ├── booking.py         # Booking request/response schemas
│   ├── customer.py        # Customer schemas
│   ├── provider.py        # Provider schemas
│   ├── service.py         # Service schemas
│   └── slot.py            # Slot schemas + status enum
├── routes/
│   ├── bookings.py        # Lock → Confirm → Cancel → Reschedule
│   ├── catalog.py         # Services & Providers
│   └── slots.py           # Available slots & generation
├── services/
│   ├── booking_service.py # Booking orchestration with retry
│   ├── catalog_service.py # Read-only lookups
│   ├── lock_service.py    # Redis distributed locking
│   └── slot_service.py    # Slot CRUD + state machine
└── main.py                # FastAPI app factory + lifespan
scripts/
└── seed.py                # Populate sample data
```

## Prerequisites

| Dependency | Version |
|------------|---------|
| Python     | 3.11+   |
| MongoDB    | 6.0+    |
| Redis      | 7.0+    |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment (edit .env as needed)
cp .env .env.local

# 3. Seed sample data
python -m scripts.seed

# 4. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: **http://localhost:8000/docs**

## API Reference

### Catalog

| Method | Endpoint                     | Description            |
|--------|------------------------------|------------------------|
| GET    | `/api/v1/services`           | List all services      |
| GET    | `/api/v1/providers`          | List providers         |
| GET    | `/api/v1/providers/{id}`     | Get provider details   |

### Slots

| Method | Endpoint                     | Description                  |
|--------|------------------------------|------------------------------|
| GET    | `/api/v1/slots`              | Available slots for provider + date |
| POST   | `/api/v1/slots/generate`     | Generate slots (admin)       |

### Bookings (2-Phase)

| Method | Endpoint                                  | Description           |
|--------|-------------------------------------------|-----------------------|
| POST   | `/api/v1/slots/lock`                      | Lock a slot (step 1)  |
| POST   | `/api/v1/bookings`                        | Confirm booking (step 2) |
| PATCH  | `/api/v1/bookings/{id}/cancel`            | Cancel booking        |
| PATCH  | `/api/v1/bookings/{id}/reschedule`        | Reschedule booking    |

## Booking Flow

```
1. Client GETs available slots
2. Client POSTs /slots/lock         → receives lock_id (valid 5 min)
3. Client POSTs /bookings           → passes lock_id to confirm
```

### Concurrency Guarantees

- **Redis SET NX EX** — atomic distributed lock acquire with auto-expiry
- **Lua script unlock** — only the lock owner can release
- **MongoDB unique compound index** on `(provider_id, date, time)` — prevents double-booking at DB level
- **Optimistic concurrency** — slot version field + status guards on updates
- **Partial unique index** on bookings — only `confirmed` bookings enforce uniqueness
- **Retry loop** — configurable retries on transient failures

## Environment Variables

| Variable                | Default                       | Description                    |
|-------------------------|-------------------------------|--------------------------------|
| `MONGO_URI`             | `mongodb://localhost:27017`   | MongoDB connection string      |
| `MONGO_DB_NAME`         | `appointment_db`              | Database name                  |
| `REDIS_URL`             | `redis://localhost:6379/0`    | Redis connection URL           |
| `SLOT_LOCK_TTL_SECONDS` | `300`                         | Lock expiry in seconds         |
| `MAX_BOOKING_RETRIES`   | `3`                           | Retries on transient errors    |
| `DEBUG`                 | `false`                       | Enable debug logging           |
