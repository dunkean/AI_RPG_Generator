"""ComfyUI transport errors and bounded polling with simulated HTTP."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.image.comfyui.client import ComfyUIClient


def response(status, payload, path="/history/test"):
    return httpx.Response(
        status, json=payload, request=httpx.Request("GET", f"http://comfy.test{path}"),
    )


@pytest.fixture
def http_client():
    with patch("src.image.comfyui.client.httpx.AsyncClient") as client:
        connection = AsyncMock()
        client.return_value.__aenter__.return_value = connection
        connection.post.return_value = response(200, {"prompt_id": "test"}, "/prompt")
        yield connection


async def test_polling_raises_http_error(http_client):
    http_client.get.return_value = response(503, {})
    with pytest.raises(httpx.HTTPStatusError):
        await ComfyUIClient().execute_workflow({"prompt": {}})


async def test_polling_has_overall_deadline(http_client):
    http_client.get.return_value = response(200, {})
    with pytest.raises(TimeoutError):
        await ComfyUIClient(timeout=0.01, poll_interval=10).execute_workflow({"prompt": {}})


async def test_downloads_saved_image(http_client):
    image_response = httpx.Response(
        200, content=b"PNG", request=httpx.Request("GET", "http://comfy.test/view"),
    )
    http_client.get.side_effect = [
        response(200, {"test": {"outputs": {"10": {"images": [{"filename": "test.png"}]}}}}),
        image_response,
    ]
    assert await ComfyUIClient().execute_workflow({"prompt": {}}) == b"PNG"
