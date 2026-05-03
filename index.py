import os
import time
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request
from dotenv import load_dotenv

try:
    from twilio.rest import Client
except Exception:
    Client = None

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
if not os.getenv("ALERT_PHONE_NUMBER"):
    load_dotenv(BASE_DIR / ".env.example", override=False)

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
ALERT_PHONE_NUMBER = os.getenv("ALERT_PHONE_NUMBER")
ALLOW_DRY_RUN = os.getenv("ALLOW_DRY_RUN", "true").lower() == "true"
COOLDOWN_S = int(os.getenv("COOLDOWN_S", "60"))

recent_calls: dict[str, float] = {}


def escape_for_twiml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/", methods=["GET", "OPTIONS"])
def home():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify(message="API working 🚀")


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify(ok=True)


@app.route("/api/alert-call", methods=["POST", "OPTIONS"])
def alert_call():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    moisture = data.get("moisture")
    to = data.get("to") or ALERT_PHONE_NUMBER
    message = data.get("message") or "Alert. Baby diaper is full. Please change it immediately."

    if not to:
        return jsonify(error="No target phone number provided or configured."), 400

    if moisture is not None:
        try:
            moisture_value = float(moisture)
        except Exception as exc:
            return jsonify(error="Invalid moisture value"), 400
        if moisture_value <= 70:
            return jsonify(error="Moisture must be > 70 to trigger call"), 400

    now = time.time()
    last_call = recent_calls.get(to, 0.0)
    if now - last_call < COOLDOWN_S:
        return jsonify(error="Cooldown active for this target number"), 429

    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and Client):
        if ALLOW_DRY_RUN:
            fake_sid = f"DRYRUN-{int(now * 1000)}"
            recent_calls[to] = now
            return jsonify(success=True, callSid=fake_sid, message="Dry-run simulated call")
        return jsonify(error="Twilio credentials not configured on server"), 500

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    twiml = f'<Response><Say voice="alice">{escape_for_twiml(message)}</Say></Response>'

    try:
        call = client.calls.create(
            to=to,
            from_=TWILIO_PHONE_NUMBER,
            twiml=twiml,
        )
        recent_calls[to] = now
        return jsonify(success=True, callSid=call.sid)
    except Exception as exc:
        return jsonify(error=str(exc)), 500


# Vercel can import the Flask app directly.
handler = app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3002")), debug=True)