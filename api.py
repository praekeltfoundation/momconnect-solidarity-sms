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


@app.route("/")
async def health(request):
    return json({"status": "ok"})


@app.route("/", methods=["POST"])
async def message(request):
    return json({"TODO": "TODO", "request": request.json})


monitor(app).expose_endpoint()

if __name__ == "__main__":
    app.run()
