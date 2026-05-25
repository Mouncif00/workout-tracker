# IronLog — Workout Tracker API · Phase 2

A production-ready FastAPI backend for tracking workouts, exercises, and fitness progress. Features Redis-cached dashboard stats and an AI-powered weekly progress summary via OpenAI.

---

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.111 |
| Database | PostgreSQL 16 (SQLAlchemy 2.0 ORM) |
| Migrations | Alembic |
| Caching | Redis 7 (graceful fallback if unavailable) |
| AI Summary | OpenAI gpt-3.5-turbo |
| Scheduler | APScheduler (weekly background task) |
| Auth | JWT (python-jose + passlib bcrypt) |
| Validation | Pydantic v2 |
| Tests | pytest + SQLite in-memory |
| Container | Docker Compose |

---

## Project Structure

```
workout-tracker/
├── app/
│   ├── core/
│   │   ├── config.py         # Pydantic settings (reads .env)
│   │   ├── database.py       # SQLAlchemy engine + session
│   │   ├── cache.py          # Redis helper (get/set/delete)
│   │   ├── security.py       # JWT encode/decode, bcrypt, auth dependency
│   │   └── scheduler.py      # APScheduler weekly AI task
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── exercise.py
│   │   └── workout.py        # Workout + WorkoutExercise
│   ├── schemas/              # Pydantic request/response schemas
│   │   ├── user.py
│   │   ├── exercise.py
│   │   ├── workout.py
│   │   └── dashboard.py
│   ├── routers/              # FastAPI route handlers
│   │   ├── auth.py           # POST /signup, /login, GET /me
│   │   ├── exercises.py      # GET/POST /exercises
│   │   ├── workouts.py       # Full CRUD + progress report
│   │   └── dashboard.py      # GET /dashboard, POST /summary/generate
│   ├── services/             # Business logic layer
│   │   ├── auth_service.py
│   │   ├── workout_service.py
│   │   ├── dashboard_service.py  # Redis caching logic
│   │   └── ai_summary_service.py # OpenAI integration
│   └── main.py               # App factory, CORS, router wiring
├── alembic/                  # Database migrations
│   └── versions/001_initial.py
├── scripts/
│   └── seed_exercises.py     # 40+ exercises seeder
├── tests/
│   ├── conftest.py           # SQLite fixtures, test isolation
│   ├── test_auth.py          # 9 auth tests
│   ├── test_exercises.py     # 6 exercise tests
│   └── test_workouts.py      # 12 workout CRUD tests
├── frontend/
│   └── index.html            # Single-page AI-generated frontend
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
# Edit .env: set DATABASE_URL, REDIS_URL, SECRET_KEY, OPENAI_API_KEY
```

### 2. Docker (recommended — one command)

```bash
docker compose up --build
```

This starts PostgreSQL, Redis, runs migrations, seeds exercises, and serves the API on **http://localhost:8000**.

### 3. Manual (local dev)

```bash
# Install deps
pip install -r requirements.txt

# Start Postgres + Redis (or adjust .env to point elsewhere)
# Run migrations
alembic upgrade head

# Seed exercises
python scripts/seed_exercises.py

# Start API
uvicorn app.main:app --reload
```

---

## API Endpoints

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/docs`

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/signup` | ❌ | Register. Returns JWT + user |
| POST | `/auth/login` | ❌ | Login. Returns JWT + user |
| GET | `/auth/me` | ✅ | Get current user profile |

**Signup request:**
```json
{
  "email": "user@example.com",
  "username": "ironman",
  "password": "strongpass123",
  "full_name": "Tony Stark"
}
```

**Login request:**
```json
{ "email": "user@example.com", "password": "strongpass123" }
```

All protected endpoints require `Authorization: Bearer <token>` header.

---

### Exercises

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/exercises/` | List all (filter: `?category=strength&muscle_group=legs&search=squat`) |
| GET | `/exercises/{id}` | Get by ID |
| POST | `/exercises/` | Add new exercise to library |

---

### Workouts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/workouts/` | List user's workouts (filter: `?status=scheduled`) |
| POST | `/workouts/` | Create workout with exercises |
| GET | `/workouts/{id}` | Get full workout detail |
| PATCH | `/workouts/{id}` | Update title, notes, status, schedule |
| DELETE | `/workouts/{id}` | Delete workout |
| POST | `/workouts/{id}/exercises` | Add exercise to existing workout |
| DELETE | `/workouts/{id}/exercises/{we_id}` | Remove exercise entry |
| GET | `/workouts/reports/progress` | Progress time-series (filter by muscle/date) |

**Create workout:**
```json
{
  "title": "Push Day",
  "scheduled_at": "2025-06-01T09:00:00",
  "notes": "Focus on form",
  "exercises": [
    { "exercise_id": 1, "sets": 4, "reps": 8, "weight_kg": 80.0 },
    { "exercise_id": 3, "sets": 3, "reps": 12, "weight_kg": 20.0 }
  ]
}
```

**Mark complete:**
```json
{ "status": "completed", "completed_at": "2025-06-01T10:15:00", "duration_minutes": 75 }
```

---

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/` | Aggregated stats (Redis-cached 5 min) |
| POST | `/dashboard/summary/generate` | Force-generate AI weekly summary |

**Dashboard response includes:**
- `workouts_this_week`, `workouts_this_month`, `total_workouts_all_time`
- `total_volume_this_week_kg`, `streak_days`
- `muscle_group_breakdown` — sets per muscle group
- `recent_personal_records` — max weight per exercise (last 30 days)
- `weekly_progress` — 8-week bar chart data
- `weekly_ai_summary` — AI-generated paragraph
- `cached: true/false` — whether response came from Redis

---

## Redis Caching

Dashboard stats are cached for **5 minutes** per user. When a workout is created/updated/deleted, the cache is invalidated automatically via `cache_delete_pattern(f"dashboard:{user_id}:*")`.

If Redis is unavailable, all cache operations silently no-op and the API continues to function normally from the database.

Cache TTLs (configurable in `app/core/cache.py`):
- Dashboard: 300s (5 min)
- Exercise list: 3600s (1 hr)
- Weekly AI summary: 3600s (1 hr)

---

## AI Weekly Summary

The `ai_summary_service` collects:
- Number of training days this week
- Exercises performed with max weight and total volume
- New personal records vs. last week

It sends a structured prompt to `gpt-3.5-turbo` and stores the plain-English result in `users.weekly_summary`.

A background APScheduler task fires every Sunday at 00:00 UTC to regenerate summaries for all active users.

If `OPENAI_API_KEY` is not set, a deterministic rule-based fallback is used instead.

---

## Running Tests

```bash
pytest tests/ -v
```

Tests use an **in-memory SQLite** database — no running Postgres or Redis needed. Each test gets a clean slate via `autouse` table truncation.

```
27 passed in 7s
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | postgres://... | PostgreSQL connection string |
| `REDIS_URL` | redis://localhost:6379/0 | Redis URL |
| `SECRET_KEY` | (change me!) | JWT signing secret |
| `ALGORITHM` | HS256 | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | Token lifetime |
| `OPENAI_API_KEY` | (empty) | OpenAI key for AI summaries |
| `APP_ENV` | development | `development` or `production` |
| `DEBUG` | true | Enable debug mode |

---

## Frontend

A single-page app lives in `frontend/index.html`. Open it in a browser while the API is running on `localhost:8000`. It provides:

- Login / Sign-up forms
- Dashboard with stats, bar chart, muscle breakdown, and AI summary
- Workout list with status filtering
- Workout creation modal (add exercises with sets/reps/weight)
- Exercise library with search and muscle-group filter
- Progress report page

> **Note:** In production, serve `frontend/index.html` via any static host (Nginx, GitHub Pages, Vercel) and update the `API` constant at the top of the file to point to your deployed API URL.

---

## What's Next — Phase 3 (Security)

- [ ] JWT refresh tokens
- [ ] Role-based access control (admin vs user)
- [ ] Input sanitisation middleware
- [ ] Rate limiting on `/auth/*` endpoints (slowapi)
- [ ] HTTPS enforcement in production config
