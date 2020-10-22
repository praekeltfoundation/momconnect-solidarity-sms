import base64
import hmac
from functools import wraps
from hashlib import sha256
from os import getenv
from urllib.parse import urljoin

import httpx
from sanic import Sanic
from sanic.response import json
from sanic_prometheus import monitor
from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.sanic import SanicIntegration

SENTRY_DSN = getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_init(dsn=SENTRY_DSN, integrations=[SanicIntegration()])


ID_NUMBER_PROMPT = (
    "MomConnect thanks you. Please reply with your ID number. This reply message is "
    "free & won't cost you anything. We need your ID number to make sure it's you"
)
THANKS_REPLY = (
    "Thank you for your time! If you qualify for the benefit, you'll receive a message "
    "from The Solidarity Fund. Please don't share your banking details with anyone"
)

app = Sanic(__name__)

http_client = httpx.Client()


def validate_hmac(f):
    @wraps(f)
    async def decorated_function(request, *args, **kwargs):
        try:
            signature = request.headers["X-Turn-Hook-Signature"]
            assert signature
        except (KeyError, AssertionError):
            return json({"authorization": "X-Turn-Hook-Signature header required"}, 401)

        h = hmac.new(getenv("TURN_HMAC_SECRET").encode(), request.body, sha256)
        if not hmac.compare_digest(base64.b64encode(h.digest()), signature.encode()):
            return json(
                {"authorization": "Invalid value for X-Turn-Hook-Signature"}, 403
            )

        return await f(request, *args, **kwargs)

    return decorated_function


@app.route("/")
async def health(request):
    return json({"status": "ok"})


async def send_sms(to_addr, claim_id, body):
    headers = {
        "Authorization": "Bearer {}".format(getenv("TURN_TOKEN")),
        "Content-Type": "application/json",
        "x-turn-fallback-channel": "1",
        "X-Turn-Claim-Extend": claim_id,
    }

    data = {
        "preview_url": False,
        "recipient_type": "individual",
        "to": to_addr,
        "type": "text",
        "text": {"body": body},
    }
    return await http_client.post(
        urljoin(getenv("TURN_URL"), "v1/messages"), headers=headers, json=data
    )


@app.route("/", methods=["POST"])
@validate_hmac
async def message(request):
    claim_id = request.headers.get("X-Turn-Claim")
    for message in request.json.get("messages", []):
        text_body = message.get("text", {}).get("body", "").lower().strip()
        wa_id = message.get("from")

        if text_body == "fund":
            await send_sms(to_addr=wa_id, claim_id=claim_id, body=ID_NUMBER_PROMPT)

    return json({})


if __name__ == "__main__":
    monitor(app).expose_endpoint()
    app.run()
