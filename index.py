import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import uvicorn

try:
    from twilio.rest import Client
except Exception:
    Client = None

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
if not os.getenv("ALERT_PHONE_NUMBER"):
    load_dotenv(BASE_DIR / ".env.example", override=False)

app = FastAPI(title="Smart Dipper Calling Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
ALERT_PHONE_NUMBER = os.getenv("ALERT_PHONE_NUMBER") or "+918791752379"
ALLOW_DRY_RUN = os.getenv("ALLOW_DRY_RUN", "true").lower() == "true"
COOLDOWN_S = int(os.getenv("COOLDOWN_S", "60"))

recent_calls: dict[str, float] = {}


class AlertRequest(BaseModel):
    moisture: Optional[float] = None
    to: Optional[str] = None
    message: Optional[str] = None


def escape_for_twiml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


@app.get("/")
def home():
    return {"message": "API working 🚀"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/alert-call")
def alert_call(req: AlertRequest):
    to = req.to or ALERT_PHONE_NUMBER
    message = req.message or "Alert. Baby diaper is full. Please change it immediately."

    if not to:
        raise HTTPException(
            status_code=400,
            detail="No target phone number provided or configured.",
        )

    if req.moisture is not None:
        try:
            moisture = float(req.moisture)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid moisture value") from exc
        if moisture <= 70:
            raise HTTPException(
                status_code=400,
                detail="Moisture must be > 70 to trigger call",
            )

    now = time.time()
    last_call = recent_calls.get(to, 0.0)
    if now - last_call < COOLDOWN_S:
        raise HTTPException(
            status_code=429,
            detail="Cooldown active for this target number",
        )

    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and Client):
        if ALLOW_DRY_RUN:
            fake_sid = f"DRYRUN-{int(now * 1000)}"
            recent_calls[to] = now
            return {
                "success": True,
                "callSid": fake_sid,
                "message": "Dry-run simulated call",
            }
        raise HTTPException(
            status_code=500,
            detail="Twilio credentials not configured on server",
        )

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    twiml = f'<Response><Say voice="alice">{escape_for_twiml(message)}</Say></Response>'

    try:
        call = client.calls.create(
            to=to,
            from_=TWILIO_PHONE_NUMBER,
            twiml=twiml,
        )
        recent_calls[to] = now
        return {"success": True, "callSid": call.sid}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Vercel can import the ASGI app directly.
handler = app


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "3002")))