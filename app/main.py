import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, campaigns, contact_lists, contacts, emails, webhooks
from app.config import engine

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Only show STEP logs from campaigns route
logging.getLogger('app.routes.campaigns').setLevel(logging.INFO)

app = FastAPI(
    title="University Outreach — Python API",
    version="0.2.0",
    root_path="/api"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(campaigns.router)
app.include_router(contact_lists.router)
app.include_router(emails.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    return {"status": "ok"}