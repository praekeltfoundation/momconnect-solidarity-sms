import base64
import hmac
from functools import wraps
from hashlib import sha256
from os import getenv

from sanic import Sanic
from sanic.response import json
from sanic_prometheus import monitor
from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.sanic import SanicIntegration

SENTRY_DSN = getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_init(dsn=SENTRY_DSN, integrations=[SanicIntegration()])

app = Sanic(__name__)


def validate_hmac(f):
    @wraps(f)
    async def decorated_function(request, *args, **kwargs):
        try:
            signature = request.headers["X-Turn-Hook-Signature"]
            assert signature
        except (KeyError, AssertionError):
            return json({"authorization": "X-Turn-Hook-Signature header required"}, 401)

        h = hmac.new(getenv("HMAC_SECRET").encode(), request.body, sha256)
        if not hmac.compare_digest(base64.b64encode(h.digest()), signature.encode()):
            return json(
                {"authorization": "Invalid value for X-Turn-Hook-Signature"}, 403
            )

        return await f(request, *args, **kwargs)

    return decorated_function


@app.route("/")
async def health(request):
    return json({"status": "ok"})


@app.route("/", methods=["POST"])
@validate_hmac
async def message(request):
    return json({"TODO": "TODO", "request": request.json})


monitor(app).expose_endpoint()

if __name__ == "__main__":
    app.run()
