# Smart Dipper Python Backend

This backend exposes a FastAPI app for health checks and Twilio calling. It supports a dry-run mode for local development when Twilio credentials are missing.

## Endpoints

- `GET /` returns a simple API status message.
- `GET /health` returns `{"ok": true}`.
- `POST /api/alert-call` triggers a Twilio voice call or a dry-run simulation.

## Local setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your Twilio credentials.

3. Run the API locally from the `api` folder:

```bash
uvicorn index:app --host 0.0.0.0 --port 3002 --reload
```

4. Test the health check:

```bash
curl http://localhost:3002/health
```

5. Test the calling endpoint:

```bash
curl -X POST http://localhost:3002/api/alert-call -H "Content-Type: application/json" -d '{"moisture":75}'
```

## Environment variables

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `ALERT_PHONE_NUMBER`
- `ALLOW_DRY_RUN`
- `COOLDOWN_S`
"# smart_dipper_backend" 
