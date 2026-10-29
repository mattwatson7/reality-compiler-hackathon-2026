"""Bound upload request bytes before Starlette spools multipart files to disk."""

from fastapi import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class UploadBodyLimit:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != "/api/jobs/upload":
            await self.app(scope, receive, send)
            return
        length = dict(scope.get("headers", [])).get(b"content-length")
        if length is not None:
            try:
                declared = int(length)
                if declared < 0:
                    raise ValueError("negative content length")
            except ValueError:
                await JSONResponse({"detail": "Invalid Content-Length"}, 400)(scope, receive, send)
                return
            if declared > self.max_bytes:
                await JSONResponse({"detail": "Upload request exceeds byte limit"}, 413)(
                    scope, receive, send
                )
                return
        received = 0

        async def bounded_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise HTTPException(413, "Upload request exceeds byte limit")
            return message

        await self.app(scope, bounded_receive, send)
