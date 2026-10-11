"""FastAPI application entrypoint.

In development the Vite dev server (5173) serves the UI and proxies /api here.
For deployment the built frontend (frontend/dist) is served by this same app, so
one process on one port covers everything and the browser stays same-origin.
"""
import base64
import hmac
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import PROJECT_ROOT, init_db
from app.routers import cards, categories, review

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# --- optional HTTP Basic auth -------------------------------------------------
# Off unless BOTH env vars are set, so local development and the test-suite stay
# login-free. Turn it on before putting this on the public internet: there is no
# user model, it is a single shared password guarding the whole app.
APP_USER = os.getenv("APP_USER", "").strip()
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()
AUTH_ENABLED = bool(APP_USER and APP_PASSWORD)
AUTH_REALM = "flashcards"
# Left open so container/orchestrator healthchecks can probe without credentials.
AUTH_EXEMPT_PATHS = {"/api/health"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and the default category on startup."""
    init_db()
    yield


app = FastAPI(
    title="知识卡片复习工具 API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    if not AUTH_ENABLED or request.url.path in AUTH_EXEMPT_PATHS:
        return await call_next(request)
    # Never challenge CORS preflights.
    if request.method == "OPTIONS":
        return await call_next(request)

    header = request.headers.get("authorization", "")
    if header.startswith("Basic "):
        try:
            decoded = base64.b64decode(header[6:]).decode("utf-8")
            user, _, password = decoded.partition(":")
        except Exception:  # noqa: BLE001 - malformed header means "not logged in"
            user = password = ""
        # Compare as bytes: hmac.compare_digest rejects non-ASCII str, and a
        # Chinese password is entirely plausible here.
        if hmac.compare_digest(
            user.encode("utf-8"), APP_USER.encode("utf-8")
        ) and hmac.compare_digest(password.encode("utf-8"), APP_PASSWORD.encode("utf-8")):
            return await call_next(request)

    return JSONResponse(
        {"detail": "需要登录"},
        status_code=401,
        headers={"WWW-Authenticate": f'Basic realm="{AUTH_REALM}", charset="UTF-8"'},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def cache_headers(request: Request, call_next):
    """Cache directives that match how Vite names its output.

    Vite fingerprints everything under /assets, so those files can be cached
    forever. index.html must NOT be: it points at the current hashes, and a
    cached copy keeps requesting files that a later deploy has deleted — the
    classic blank-page-after-deploy bug.
    """
    response = await call_next(request)

    if response.status_code >= 400:
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    path = request.url.path
    content_type = response.headers.get("content-type", "")
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif content_type.startswith("text/html"):
        # "no-cache" still allows storing, it just forces revalidation.
        response.headers["Cache-Control"] = "no-cache"
    return response

app.include_router(categories.router)
app.include_router(cards.router)
app.include_router(review.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


# --- serve the built SPA (production) ----------------------------------------
# Skipped when frontend/dist is missing, which is the normal state during
# development and in the test-suite.
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
INDEX_HTML = FRONTEND_DIST / "index.html"

if INDEX_HTML.is_file():
    _assets = FRONTEND_DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """Serve a real file when one exists, otherwise hand back index.html.

        Registered last, so /api/*, /docs and /openapi.json are matched first.
        """
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        dist = FRONTEND_DIST.resolve()
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)
        return FileResponse(INDEX_HTML)
