import os
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .db import database, default_path, initialize
from .response_docs import install
from .routers import content, events, groups, polls, tickets, users


def create_app(database_path=None, rate_limit=True):
    path = str(database_path or default_path())

    @asynccontextmanager
    async def lifespan(app):
        initialize(path)
        yield

    app = FastAPI(
        title="My Social Networks API",
        version="2.0.0",
        lifespan=lifespan,
        description="API de gestion de communautés et d'événements. Montants en centimes EUR. "
        "Dates ISO 8601 avec fuseau obligatoire. Authentification Bearer via /api/v1/users ou /api/v1/auth/login. "
        "CRUDS = créer, lire, modifier, supprimer et rechercher. Les listes utilisent q, limit et offset.",
        responses={
            401: {"description": "Session requise, invalide ou expirée"},
            403: {"description": "Droits insuffisants"},
            404: {"description": "Ressource absente ou inaccessible"},
            409: {"description": "Conflit métier ou unicité"},
            422: {"description": "Données invalides"},
            429: {"description": "Trop de tentatives"},
        },
    )
    app.state.database_path = path
    buckets = defaultdict(deque)
    lock = Lock()

    @app.middleware("http")
    async def protections(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                size = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse({"detail": "Content-Length invalide"}, 400)
            if size > 1_048_576:
                return JSONResponse({"detail": "Corps trop volumineux"}, 413)
        limited = request.url.path in {"/api/v1/auth/login", "/api/v1/users"} or request.url.path.endswith(
            "/tickets"
        )
        if rate_limit and limited and request.method == "POST":
            ip = request.client.host if request.client else "unknown"
            now = time.monotonic()
            with lock:
                # Expire unused keys, so attacker-controlled client diversity cannot grow this map forever.
                for key in list(buckets):
                    if not buckets[key] or buckets[key][-1] < now - 60:
                        del buckets[key]
                bucket = buckets[(ip, request.url.path)]
                while bucket and bucket[0] < now - 60:
                    bucket.popleft()
                if len(bucket) >= 30:
                    return JSONResponse(
                        {"detail": "Trop de tentatives, réessayez dans une minute"},
                        429,
                        headers={"Retry-After": "60"},
                    )
                bucket.append(now)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity(request, exc):
        return JSONResponse(
            {"detail": "Conflit : valeur déjà utilisée ou contrainte relationnelle non respectée"}, 409
        )

    @app.exception_handler(sqlite3.OperationalError)
    async def database_error(request, exc):
        if "locked" in str(exc):
            return JSONResponse(
                {"detail": "Base temporairement occupée, veuillez réessayer"},
                503,
                headers={"Retry-After": "1"},
            )
        return JSONResponse({"detail": "Erreur de base de données"}, 500)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Do not echo credentials, tokens or other submitted personal data in validation errors.
        return JSONResponse(
            {"detail": [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]}, 422
        )

    @app.get("/health", tags=["Exploitation"], summary="Vérifier le service et la base")
    def health(request: Request):
        gen = database(request)
        db = next(gen)
        try:
            db.execute("SELECT 1").fetchone()
        finally:
            gen.close()
        return {"status": "ok", "version": "2.0.0"}

    for router in [users.router, groups.router, events.router, content.router, polls.router, tickets.router]:
        app.include_router(router, prefix="/api/v1")
    install(app)
    return app


app = create_app(rate_limit=os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false")
