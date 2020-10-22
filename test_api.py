import base64
import hmac
import json
import os
from hashlib import sha256

import pytest
import sanic

from api import ID_NUMBER_PROMPT, app


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
    os.environ["TURN_HMAC_SECRET"] = "testsecret"
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
    os.environ["TURN_HMAC_SECRET"] = "testsecret"
    data = {"test": "data"}
    request, response = await app.asgi_client.post(
        "/", headers={"X-Turn-Hook-Signature": generate_signature(data)}, json=data
    )
    assert response.status == 200
    assert response.json() == {}


@pytest.fixture
def turn_mock_server(loop, sanic_client):
    mock_turn = sanic.Sanic("mock_turn")
    mock_turn.msgs = []

    @mock_turn.route("/v1/messages", methods=["POST"])
    async def messages(request):
        mock_turn.msgs.append(request)
        return sanic.response.json({})

    return loop.run_until_complete(sanic_client(mock_turn))


@pytest.mark.asyncio
async def test_keyword_message(turn_mock_server):
    """
    A keyword message should send the ID number prompt response
    """
    os.environ["TURN_HMAC_SECRET"] = "testsecret"
    os.environ["TURN_URL"] = f"http://{turn_mock_server.host}:{turn_mock_server.port}"
    os.environ["TURN_TOKEN"] = "testtoken"
    data = {"messages": [{"from": "27820001001", "text": {"body": "fund"}}]}
    request, response = await app.asgi_client.post(
        "/",
        headers={
            "X-Turn-Hook-Signature": generate_signature(data),
            "X-Turn-Claim": "claimid",
        },
        json=data,
    )
    assert response.status == 200
    assert response.json() == {}
    [msg] = turn_mock_server.app.msgs
    assert msg.headers["X-Turn-Claim-Extend"] == "claimid"
    assert msg.headers["x-turn-fallback-channel"] == "1"
    assert msg.headers["Authorization"] == "Bearer testtoken"
    assert msg.json == {
        "preview_url": False,
        "recipient_type": "individual",
        "to": "27820001001",
        "type": "text",
        "text": {"body": ID_NUMBER_PROMPT},
    }
