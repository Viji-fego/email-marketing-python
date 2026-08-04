# Quick Start Guide for Developers

New to this project? Start here.

## Setup (One Time)

```bash
# 1. Clone and enter directory
cd email-marketing-python

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Mac/Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
copy .env.example .env
# Edit .env and fill in:
# - BREVO_API_KEY
# - BREVO_SENDER_EMAIL
# - DATABASE_URL (or use default SQLite)
# - JWT_SECRET

# 6. Setup database
alembic upgrade head

# 7. Start the app
uvicorn app.main:app --reload --port 8001
```

API docs available at: http://localhost:8001/docs

---

## Common Tasks

### Start Development Server
```bash
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8001
```

### Add a New API Endpoint

**1. Create model** (if needed): `app/models/your_model.py`

```python
from sqlalchemy import Column, String, DateTime
from app.models.base import Base, gen_uuid, utcnow

class YourModel(Base):
    __tablename__ = "your_models"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)
```

**2. Export model**: Edit `app/models/__init__.py`

```python
from app.models.your_model import YourModel
__all__ = [..., "YourModel"]
```

**3. Create migration**:
```bash
alembic revision --autogenerate -m "Add YourModel table"
alembic upgrade head
```

**4. Create route**: `app/routes/your_models.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import YourModel

router = APIRouter(prefix="/api/your-models", tags=["your-models"])

@router.post("")
def create_item(name: str, db: Session = Depends(get_db)):
    item = YourModel(name=name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name}
```

**5. Register route**: Edit `app/main.py`

```python
from app.routes import your_models
app.include_router(your_models.router)
```

**6. Test it**:
```bash
curl -X POST http://localhost:8001/api/your-models?name=Test
```

### Modify an Existing Model

**Example: Add `status` field to `Contact`**

**1. Edit model**: `app/models/contact.py`

```python
status = Column(String(50), default="active")
```

**2. Create migration**:
```bash
alembic revision --autogenerate -m "Add status to contacts"
alembic upgrade head
```

**3. That's it!** Routes automatically see the new field.

### Run Tests (when you add them)

```bash
pytest tests/
pytest tests/test_auth.py -v
pytest tests/test_contacts.py::test_import_contacts -v
```

### Database Operations

**View current migration state:**
```bash
alembic current
```

**See migration history:**
```bash
alembic history
```

**Rollback last migration:**
```bash
alembic downgrade -1
```

**Check database health:**
```python
# In Python:
from app.models import User
from app.database import SessionLocal

db = SessionLocal()
users = db.query(User).all()
print(f"Total users: {len(users)}")
db.close()
```

---

## Project Structure (Quick Reference)

```
📁 app/models/              ← Add new models here
  📄 __init__.py           (export all models)
  📄 base.py              (utilities)
  📄 user.py
  📄 contact.py
  📄 campaign.py
  
📁 app/routes/             ← Add new endpoints here
  📄 auth.py              (login/register)
  📄 contacts.py          (contact management)
  📄 campaigns.py         (campaign management)
  📄 emails.py            (email sending)
  
📁 app/services/           ← Business logic
  📄 brevo_service.py     (email provider)
  
📁 alembic/versions/       ← Auto-generated migrations
  📄 71f3c40e5aff_initial...py

📄 app/main.py             ← FastAPI app setup
📄 app/database.py         ← Database connection
📄 app/config.py           ← Settings from .env
📄 app/deps.py             ← Dependency injection
📄 .env                    ← Your secrets (not in git)
📄 requirements.txt        ← Python dependencies
```

---

## Common Patterns

### Query a Model

```python
from app.models import Contact
from app.database import SessionLocal

db = SessionLocal()

# Get all
contacts = db.query(Contact).all()

# Get one
contact = db.get(Contact, contact_id)

# Filter
contact = db.query(Contact).filter(Contact.email == "user@example.com").first()

# Pagination
page_size = 10
page = 1
contacts = db.query(Contact).offset((page-1)*page_size).limit(page_size).all()

db.close()
```

### Create/Update/Delete

```python
from app.models import Contact
from app.database import SessionLocal

db = SessionLocal()

# Create
contact = Contact(name="Jane", email="jane@mit.edu", university="MIT")
db.add(contact)
db.commit()
db.refresh(contact)
print(f"Created: {contact.id}")

# Update
contact.name = "Jane Smith"
db.commit()

# Delete
db.delete(contact)
db.commit()

db.close()
```

### Working with Relationships

```python
from app.models import CampaignContact, Campaign, Contact

db = SessionLocal()
cc = db.get(CampaignContact, cc_id)

# Access related models
campaign = cc.campaign
contact = cc.contact

print(f"Campaign: {campaign.name}")
print(f"Contact: {contact.email}")

db.close()
```

---

## Debugging Tips

### Check what's in database
```bash
# MySQL
mysql -h localhost -u root -p your_database

# SQLite (if using local db)
sqlite3 app.db
> .tables
> .schema contacts
> SELECT * FROM contacts LIMIT 5;
```

### Enable SQL logging
```python
# Add to app/main.py
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Test an endpoint
```bash
# Register
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass123!"}'

# Login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass123!"}'
```

### Interactive API docs
Open: http://localhost:8001/docs (Swagger UI)

---

## Where to Find Things

| Need... | Look in... |
|---------|-----------|
| Database models | `app/models/*.py` |
| API endpoints | `app/routes/*.py` |
| Business logic | `app/services/*.py` |
| Database setup | `app/database.py` |
| Configuration | `app/config.py` & `.env` |
| Migrations | `alembic/versions/` |
| Documentation | Root directory (README.md, MODELS_GUIDE.md, etc.) |

---

## Documentation

- **[README.md](README.md)** — Setup, API examples
- **[MODELS_GUIDE.md](MODELS_GUIDE.md)** — How models work, best practices
- **[MIGRATIONS.md](MIGRATIONS.md)** — Quick migration reference
- **[MIGRATIONS_ADVANCED.md](MIGRATIONS_ADVANCED.md)** — Advanced migration patterns
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Complete architecture overview
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** — What changed in recent refactor

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
```bash
# Make sure you're in the right directory
pwd  # Should be email-marketing-python/

# Make sure venv is activated
.venv\Scripts\activate
```

### "Can't connect to database"
```bash
# Check .env has correct DATABASE_URL
cat .env | grep DATABASE_URL

# Or check config.py uses right default
vim app/config.py
```

### "No such table: contacts"
```bash
# Run migrations
alembic upgrade head

# Verify
alembic current
```

### "Cannot add NOT NULL column"
→ See MIGRATIONS_ADVANCED.md, section "Handling Failed Migrations"

---

## Next Steps

- [ ] Follow setup steps above
- [ ] Read [MODELS_GUIDE.md](MODELS_GUIDE.md) (10 min)
- [ ] Read [ARCHITECTURE.md](ARCHITECTURE.md) (15 min)
- [ ] Add your first endpoint (following "Add a New API Endpoint" above)
- [ ] Read [MIGRATIONS_ADVANCED.md](MIGRATIONS_ADVANCED.md) when you need advanced patterns

---

## Getting Help

- Check the docs (listed above)
- Look at existing routes for examples
- Check database schema: `alembic history`
- Ask on team Slack/Discord
