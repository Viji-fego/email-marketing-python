from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, campaigns, contacts, emails

app = FastAPI(title="University Outreach — Python API", version="0.2.0")

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


@app.get("/health")
def health():
    return {"status": "ok"}
