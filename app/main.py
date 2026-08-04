import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, campaigns, contacts, emails, webhooks
from app.debug_webhook import setup_sqlalchemy_listeners, enable_sql_echo
from app.config import engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="University Outreach — Python API", version="0.2.0")

# Enable SQLAlchemy debugging
setup_sqlalchemy_listeners()
enable_sql_echo(engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(campaigns.router)
app.include_router(emails.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    return {"status": "ok"}
