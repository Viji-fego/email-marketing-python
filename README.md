# University Outreach — Python API

Python/FastAPI backend, replacing the Node/Express one. Matches the same API
shape as the original: login-protected routes, contacts stored in a database,
campaigns, and per-contact send tracking — sending through Brevo.

## Setup

```bash
cd D:\EmailMarketingpython
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

- `BREVO_API_KEY` — from Brevo dashboard > SMTP & API > API Keys
- `BREVO_SENDER_EMAIL` — must already be a **verified sender** in your Brevo account, or sends will fail
- `BREVO_SENDER_NAME` — display name shown to recipients
- `JWT_SECRET` — set this to a long random string (used to sign login tokens)
- `DATABASE_URL` — defaults to a local SQLite file (`app.db`), no separate database server needed

## Run

```bash
uvicorn app.main:app --reload --port 8001
```

Interactive API docs: http://localhost:8001/docs

Tables are created automatically on first run (`app.db` in this folder).

## Typical flow

### 1. Create an account and log in

```bash
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fego.in","password":"Sup3rSecret!"}'
```

Response includes `accessToken` — use it as `Authorization: Bearer <token>` on every request below.
`POST /api/auth/login` with the same body logs back in later.

### 2. Import contacts

```bash
curl -X POST http://localhost:8001/api/contacts/import \
  -H "Authorization: Bearer {{accessToken}}" \
  -H "Content-Type: application/json" \
  -d '{"contacts":[{"name":"Jane","email":"jane@mit.edu","university":"MIT"}]}'
```

Matching by email — importing the same address twice updates the existing contact instead of duplicating it.

### 3. Create a campaign, then enroll contacts in it

```bash
curl -X POST http://localhost:8001/api/campaigns \
  -H "Authorization: Bearer {{accessToken}}" \
  -H "Content-Type: application/json" \
  -d '{"name":"Fall 2026 Outreach"}'

curl -X POST http://localhost:8001/api/campaigns/{{campaignId}}/enroll \
  -H "Authorization: Bearer {{accessToken}}" \
  -H "Content-Type: application/json" \
  -d '{"contactIds":["{{contactId}}"]}'
```

Enrolling returns a `campaignContactId` for each contact — this is what ties an individual send back to a specific campaign + contact for tracking.

### 4. Send one email

```bash
curl -X POST http://localhost:8001/api/emails/send \
  -H "Authorization: Bearer {{accessToken}}" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "jane@mit.edu",
    "subject": "Helping Universities Streamline Student Engagement with AI",
    "htmlContent": "<p>Hello Jane...</p>",
    "textContent": "Hello Jane...",
    "campaignContactId": "{{campaignContactId}}",
    "ctaText": "Schedule a Demo",
    "ctaUrl": "https://calendly.com"
  }'
```

`ctaText`/`ctaUrl` are rendered as a button appended to the HTML email — Brevo itself has no separate "CTA" field. If `campaignContactId` is given, the send updates that record's status to `sent` (or `failed`) and logs an `EmailEvent`.

### 5. Or: upload an Excel file and send to everyone in it, in one step

```bash
curl -X POST http://localhost:8001/api/campaigns/send-from-excel \
  -H "Authorization: Bearer {{accessToken}}" \
  -F "file=@contacts.xlsx" \
  -F "campaign_name=Fall 2026 Outreach" \
  -F "subject=Welcome to the program" \
  -F "body_html=<p>Hello! Thanks for your interest.</p>" \
  -F "body_text=Hello! Thanks for your interest." \
  -F "cta_text=Schedule a Demo" \
  -F "cta_url=https://calendly.com"
```

This does steps 2–4 automatically for every row in the file: creates the campaign, imports/updates each contact (matched by the `email` column, plus `name`/`university` if those columns exist), enrolls them, and sends — same tracking as sending one at a time.

## Data model

- **User** — login accounts (email + password)
- **Contact** — a person, unique by email
- **Campaign** — a named outreach push
- **CampaignContact** — links one contact to one campaign; `status` is `pending` / `sent` / `failed`; this is the `campaignContactId`
- **EmailEvent** — a log entry per send attempt (`sent` or `failed` for now — opens/clicks/replies via webhooks are a future step)

## Next steps (not built yet)

- Brevo webhooks to record opens/clicks/bounces/replies as `EmailEvent` rows
- Segments (the Node version's `Contact.metadata.institution`-style grouping)
- Sequences, AI writer, reply analysis — same modules as the Node version, ported one at a time
