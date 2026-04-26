import os
import sys
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parent.parent

os.environ.setdefault("REDOCENCIA_UPLOADS_DIR", "/tmp/redocencia-uploads")

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app


class ApiPrefixCompatApp:
    """Compat wrapper for Vercel Services routePrefix behavior.

    Services mounted at /api may forward requests without the /api segment.
    The existing FastAPI app routes are defined under /api, so we re-add it for
    API routes while keeping docs and OpenAPI endpoints untouched.
    """

    def __init__(self, asgi_app, passthrough_paths: Iterable[str] | None = None):
        self.asgi_app = asgi_app
        self.passthrough_paths = set(passthrough_paths or {"/docs", "/openapi.json", "/redoc"})

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.asgi_app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path and not path.startswith("/api") and path not in self.passthrough_paths:
            rewritten = dict(scope)
            rewritten["path"] = f"/api{path}" if path.startswith("/") else f"/api/{path}"
            await self.asgi_app(rewritten, receive, send)
            return

        await self.asgi_app(scope, receive, send)


app = ApiPrefixCompatApp(app)
