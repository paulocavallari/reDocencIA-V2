import os
import sys
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

os.environ.setdefault("REDOCENCIA_UPLOADS_DIR", "/tmp/redocencia-uploads")

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


class ApiPrefixCompatApp:
    def __init__(self, asgi_app, passthrough_paths: Iterable[str] | None = None):
        self.asgi_app = asgi_app
        self.passthrough_paths = set(passthrough_paths or {"/docs", "/openapi.json", "/redoc"})

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.asgi_app(scope, receive, send)
            return

        path = scope.get("path", "")
        rewritten = dict(scope)
        rewritten["root_path"] = ""

        if path and not path.startswith("/api") and path not in self.passthrough_paths:
            rewritten["path"] = f"/api{path}" if path.startswith("/") else f"/api/{path}"
        else:
            rewritten["path"] = path

        await self.asgi_app(rewritten, receive, send)


app = ApiPrefixCompatApp(app)
