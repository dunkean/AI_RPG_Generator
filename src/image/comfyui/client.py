"""ComfyUI HTTP API client — handles workflow submission, polling, and image download."""

from __future__ import annotations

import asyncio
import logging
import uuid

import httpx

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Thin async wrapper around the ComfyUI REST API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8188",
        timeout: float = 300.0,
        poll_interval: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.client_id = str(uuid.uuid4())

    async def execute_workflow(self, workflow: dict) -> bytes:
        """Submit a ComfyUI workflow, poll until complete, return image bytes.

        *workflow* is the full API-format payload (``{"prompt": {node_dict}}``)
        as returned by a WorkflowBuilder.
        """
        async with asyncio.timeout(self.timeout), httpx.AsyncClient(timeout=self.timeout) as client:
            # Submit
            resp = await client.post(f"{self.base_url}/prompt", json=workflow)
            resp.raise_for_status()
            prompt_id = resp.json()["prompt_id"]

            # Poll for completion
            while True:
                history_resp = await client.get(
                    f"{self.base_url}/history/{prompt_id}"
                )
                history_resp.raise_for_status()
                history = history_resp.json()
                if prompt_id in history:
                    status = history[prompt_id].get("status", {})
                    if status.get("status_str") == "error":
                        msgs = status.get("messages", [])
                        for msg in msgs:
                            if msg[0] == "execution_error":
                                err = msg[1].get("exception_message", "unknown")
                                node = msg[1].get("node_type", "?")
                                raise RuntimeError(
                                    f"ComfyUI {node} error: {err}"
                                )
                        raise RuntimeError(
                            "ComfyUI workflow failed (unknown error)"
                        )
                    outputs = history[prompt_id].get("outputs", {})
                    break
                await asyncio.sleep(self.poll_interval)

            # Download the first saved image
            for node_output in outputs.values():
                images = node_output.get("images", [])
                if images:
                    img_info = images[0]
                    img_resp = await client.get(
                        f"{self.base_url}/view",
                        params={
                            "filename": img_info["filename"],
                            "subfolder": img_info.get("subfolder", ""),
                            "type": img_info.get("type", "output"),
                        },
                    )
                    img_resp.raise_for_status()
                    return img_resp.content

            raise RuntimeError(
                f"No image output found for prompt_id={prompt_id}"
            )
