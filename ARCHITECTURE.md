# Project Architecture & Best Practices

## Complete Project Structure

```
email-marketing-python/
├── alembic/                         # Database migrations (Alembic)
│   ├── versions/                   # Individual migration files
│   │   └── 71f3c40e5aff_initial_migration_create_users_contacts_.py
│   ├── env.py                      # Migration configuration
│   └── alembic.ini                 # Alembic settings
│
├── app/                             # Main application
│   ├── models/                     # ⭐ Database models (individual files)
│   │   ├── __init__.py            # Exports all models
│   │   ├── base.py                # Base class + utilities
│   │   ├── user.py                # User model
│   │   ├── contact.py             # Contact model
│   │   ├── campaign.py            # Campaign model
│   │   ├── campaign_contact.py    # Junction table
│   │   └── email_event.py         # Email event log
│   │
│   ├── routes/                    # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── contacts.py           # Contact management
│   │   ├── campaigns.py          # Campaign management
│   │   └── emails.py             # Email sending
│   │
│   ├── services/                 # Business logic
│   │   ├── brevo_service.py      # Email sending via Brevo
│   │   └── excel_service.py      # Excel file parsing
│   │
│   ├── main.py                   # FastAPI app initialization
│   ├── database.py               # Database connection
│   ├── config.py                 # Configuration (from .env)
│   ├── deps.py                   # Dependency injection
│   └── security.py               # JWT, password hashing
│
├── .env                            # Environment variables (local)
├── .env.example                    # Environment template
├── requirements.txt                # Python dependencies
├── README.md                       # Setup & usage guide
├── MODELS_GUIDE.md                 # ⭐ Model architecture
├── MIGRATIONS.md                   # ⭐ Migration quick start
├── MIGRATIONS_ADVANCED.md          # ⭐ Advanced migration patterns
└── ARCHITECTURE.md                 # This file
```

## Architectural Layers

```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI)              │
│    routes/ + deps.py                    │
│  (Handle HTTP requests/responses)       │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Business Logic Layer                │
│    services/ (Brevo, Excel parsing)     │
│  (Business rules, validation)           │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│       Data Access Layer                  │
│   models/ + database.py                 │
│  (SQLAlchemy ORM, DB queries)           │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Database Layer                   │
│       MySQL (via SQLAlchemy)             │
│  (Tables, indexes, constraints)         │
└─────────────────────────────────────────┘
```

## Data Flow Example: Send Email

```
1. API Request
   POST /api/emails/send
   │
2. Route Handler (routes/emails.py)
   ├─ Parse request
   ├─ Get current user (deps.py)
   └─ Call service layer
   │
3. Business Logic (services/brevo_service.py)
   ├─ Validate email
   ├─ Format HTML with CTA button
   └─ Call Brevo API
   │
4. Data Access (models/ + database.py)
   ├─ Update CampaignContact.status = "sent"
   ├─ Create EmailEvent record
   └─ Commit transaction
   │
5. Response
   HTTP 200 {"success": true, "to": "user@example.com"}
```

## Database Relationships

```
       User
        │
        ├──→ creates Campaign
        │
        └──→ imports Contact
                │
                └──→ enrolled in CampaignContact
                     │
                     └──→ tracked by EmailEvent
```

### Model Dependencies

```
Base (base.py)
├── User ─────────────────────┐
├── Contact ───────────────┐  │
├── Campaign ───────────┐  │  │
├── CampaignContact ◄──┴──┴──┤ (references Campaign, Contact)
│                             │
└── EmailEvent ◄─────────────┘ (references CampaignContact)
```

## Import Organization

### Models (single source of truth)

```python
# ✅ Always import from app.models (uses __init__.py)
from app.models import User, Contact, Campaign, CampaignContact, EmailEvent
from app.models import Base, gen_uuid, utcnow
```

### Routes

```python
# routes/auth.py
from app.models import User
from app.database import get_db
from app.deps import get_current_user
from app.security import create_access_token
```

### Services

```python
# services/brevo_service.py
from app.config import settings
# ✅ Services don't import models directly
# They receive models from route handlers
```

## Configuration Management

```
.env (local - NOT in git)
├── BREVO_API_KEY
├── BREVO_SENDER_EMAIL
├── DATABASE_URL (MySQL connection string)
└── JWT_SECRET
    │
    ▼
config.py (Settings class)
    │
    ├─→ app/main.py (server config)
    ├─→ app/database.py (DB config)
    ├─→ app/routes/ (API behavior)
    └─→ alembic/env.py (migration config)
```

## Database Versioning

```
Code Changes
    │
    ├─ Modify: app/models/xxx.py
    ├─ Export: app/models/__init__.py
    │
    ▼
Generate Migration
    alembic revision --autogenerate -m "description"
    │
    ▼ (creates)
alembic/versions/xxxxx_description.py
    │
    ├─ upgrade() — what to run
    ├─ downgrade() — how to rollback
    │
    ▼
Apply Migration
    alembic upgrade head
    │
    ▼
Database Schema Updated
```

## Development Workflow

### Adding a New Feature

```bash
# 1. Modify model
vim app/models/campaign.py

# 2. Export from models
vim app/models/__init__.py

# 3. Generate migration
alembic revision --autogenerate -m "Add campaign_type"

# 4. Review migration
vim alembic/versions/xxxxx_add_campaign_type.py

# 5. Apply migration
alembic upgrade head

# 6. Write route handler
vim app/routes/campaigns.py

# 7. Test locally
uvicorn app.main:app --reload

# 8. Commit
git add app/models/ app/routes/ alembic/
git commit -m "Add campaign type feature"

# 9. Push to team
git push
```

### Team Pulling Latest Changes

```bash
# 1. Pull code
git pull

# 2. Apply any new migrations
alembic upgrade head

# 3. Install new dependencies (if any)
pip install -r requirements.txt

# 4. Run app
uvicorn app.main:app --reload
```

## Best Practices by Layer

### Models Layer (app/models/)

✅ **DO:**
- Keep models as pure data structures
- Use type hints (String, Integer, DateTime, etc.)
- Index foreign keys and frequently queried columns
- Use relationships for ORM convenience
- Create separate files for each entity

❌ **DON'T:**
- Add business logic to models
- Create circular dependencies between models
- Use mutable defaults (use callable like `default=utcnow`)
- Mix multiple concerns in one model file

### Routes Layer (app/routes/)

✅ **DO:**
- Handle HTTP request/response formatting
- Validate input using Pydantic models
- Use dependency injection for database sessions
- Return consistent JSON responses
- Handle 404/400/500 status codes

❌ **DON'T:**
- Add database queries directly in routes (use services)
- Duplicate validation logic across routes
- Return raw database objects (convert to JSON-serializable)
- Handle business logic in route handlers

### Services Layer (app/services/)

✅ **DO:**
- Contain business logic
- Call external APIs (Brevo, etc.)
- Validate complex business rules
- Be independent of HTTP layer

❌ **DON'T:**
- Access database directly (pass models from routes)
- Handle HTTP request/response formatting
- Create services that import each other (circular imports)

### Database Layer (app/database.py, app/models/)

✅ **DO:**
- Use transactions for multi-step operations
- Validate at database level (NOT NULL, unique, FK constraints)
- Create indexes on frequently queried columns
- Use migrations for all schema changes

❌ **DON'T:**
- Store business logic in database
- Bypass migrations for schema changes
- Rely only on app-level validation

## Scalability Path

### Phase 1: Current (Individual Models)
- ✅ 5-10 tables
- Individual model files
- Single database
- Direct route → service → model flow

### Phase 2: Growing (20+ tables)
- Consider domain-driven organization:
  ```
  app/models/
  ├── auth/
  │   ├── user.py
  │   └── token.py
  ├── contacts/
  │   ├── contact.py
  │   └── segment.py
  └── campaigns/
      ├── campaign.py
      └── template.py
  ```

### Phase 3: Enterprise (100+ tables)
- Separate services by domain
- Read replicas for analytics
- Event sourcing for audit trails
- CQRS (Command Query Responsibility Segregation)

## Testing Strategy

### Unit Tests (models)

```python
def test_user_model():
    user = User(email="test@example.com", password_hash="x", password_salt="y")
    assert user.email == "test@example.com"
```

### Integration Tests (routes)

```python
def test_register_endpoint(client, db):
    response = client.post("/api/auth/register", json={
        "email": "new@example.com",
        "password": "Secret123!"
    })
    assert response.status_code == 200
```

### Migration Tests

```python
def test_migration_up_and_down():
    command.upgrade(config, "head")
    # Verify schema...
    command.downgrade(config, "-1")
    # Verify rollback...
```

## Deployment Checklist

- [ ] All tests passing
- [ ] Migrations reviewed and tested
- [ ] Environment variables set (.env)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] App tested locally (`uvicorn app.main:app`)
- [ ] Code committed to git
- [ ] Code reviewed by team
- [ ] Deployed to staging first
- [ ] Staging verification passed
- [ ] Deployed to production
- [ ] Production logs monitored

## Summary

| Aspect | Approach | Benefit |
|--------|----------|---------|
| Models | Individual files per entity | Scalability, maintainability |
| Database | Alembic migrations | Version control, rollback support |
| API | Layered (routes → services → models) | Clean separation of concerns |
| Configuration | Environment-driven | Security, environment-specific config |
| Testing | Unit + Integration + Migration tests | Comprehensive coverage |

This architecture supports:
- ✅ Small teams (3-5 developers)
- ✅ Rapid feature development
- ✅ Safe database changes
- ✅ Easy onboarding
- ✅ Scaling to 20+ tables

For questions, see:
- [MODELS_GUIDE.md](MODELS_GUIDE.md) — Model patterns
- [MIGRATIONS.md](MIGRATIONS.md) — Quick migration start
- [MIGRATIONS_ADVANCED.md](MIGRATIONS_ADVANCED.md) — Advanced patterns
