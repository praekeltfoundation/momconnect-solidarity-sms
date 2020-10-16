import base64
import hmac
import json
import os
from hashlib import sha256
import pytest

from api import app


@pytest.mark.asyncio
async def test_health():
    request, response = await app.asgi_client.get("/")
    assert response.status == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_hmac_signature_required():
    request, response = await app.asgi_client.post("/")
    assert response.status == 401
    assert response.json() == {"authorization": "X-Turn-Hook-Signature header required"}

    request, response = await app.asgi_client.post(
        "/", headers={"X-Turn-Hook-Signature": ""}
    )
    assert response.status == 401
    assert response.json() == {"authorization": "X-Turn-Hook-Signature header required"}


@pytest.mark.asyncio
async def test_hmac_signature_invalid():
    os.environ["HMAC_SECRET"] = "testsecret"
    request, response = await app.asgi_client.post(
        "/", headers={"X-Turn-Hook-Signature": "foo"}, json={}
    )
    assert response.status == 403
    assert response.json() == {
        "authorization": "Invalid value for X-Turn-Hook-Signature"
    }


def generate_signature(data):
    h = hmac.new(b"testsecret", json.dumps(data).encode(), sha256)
    return base64.b64encode(h.digest()).decode()


@pytest.mark.asyncio
async def test_hmac_signature_valid():
    os.environ["HMAC_SECRET"] = "testsecret"
    data = {"test": "data"}
    request, response = await app.asgi_client.post(
        "/", headers={"X-Turn-Hook-Signature": generate_signature(data)}, json=data
    )
    assert response.status == 200
    assert response.json() == {"TODO": "TODO", "request": {"test": "data"}}
