import asyncio

from backend.app.limits import UploadBodyLimit


def test_upload_request_body_is_bounded_before_parsing():
    async def check(headers, chunks):
        messages = []
        iterator = iter(chunks)

        async def receive():
            return {"type": "http.request", "body": next(iterator), "more_body": True}

        async def send(message):
            messages.append(message)

        async def app(scope, receive, send):
            try:
                await receive()
                await receive()
            except Exception as exc:
                assert exc.status_code == 413
                messages.append({"blocked": True})

        scope = {"type": "http", "path": "/api/jobs/upload", "headers": headers}
        await UploadBodyLimit(app, max_bytes=3)(scope, receive, send)
        return messages

    assert asyncio.run(check([(b"content-length", b"4")], []))[0]["status"] == 413
    assert asyncio.run(check([(b"content-length", b"bad")], []))[0]["status"] == 400
    assert asyncio.run(check([], [b"12", b"34"])) == [{"blocked": True}]
