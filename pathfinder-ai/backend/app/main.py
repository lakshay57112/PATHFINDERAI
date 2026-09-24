"""PathFinder AI — FastAPI application entrypoint."""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1 import assistant, auth, careers, planning, profile
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.session import Base, SessionLocal, engine
from app.knowledge.catalog import get_catalog

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pathfinder")


def _warm_ai_stores() -> None:
    try:
        from app.graphdb.store import get_graph
        from app.rag.retriever import get_retriever

        get_graph()
        get_retriever()
    except Exception as exc:  # pragma: no cover
        log.warning("knowledge stores failed to warm: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.seed import seed_all

    catalog = get_catalog()  # fails fast on knowledge-base integrity errors
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        log.info("seed: %s", seed_all(db, catalog))
    threading.Thread(target=_warm_ai_stores, daemon=True).start()
    yield


def _setup_telemetry(app: FastAPI) -> None:
    s = get_settings()
    if not s.otel_exporter_otlp_endpoint:
        return
    try:  # pragma: no cover - optional
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": "pathfinder-api"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{s.otel_exporter_otlp_endpoint}/v1/traces")))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        log.info("OpenTelemetry tracing enabled")
    except ImportError:
        log.warning("OTEL endpoint set but opentelemetry packages are not installed")


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="PathFinder AI API", version="1.0.0", lifespan=lifespan,
                  docs_url=f"{s.api_prefix}/docs", openapi_url=f"{s.api_prefix}/openapi.json",
                  description="Personalised career discovery, skill-gap analysis, roadmaps and AI mentoring.")
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.url.path.startswith(s.api_prefix) and "cache-control" not in resp.headers:
            resp.headers["Cache-Control"] = "no-store"  # user data must not be cached by intermediaries
        return resp

    register_error_handlers(app)
    for r in (auth.router, profile.router, careers.router, planning.router, assistant.router):
        app.include_router(r, prefix=s.api_prefix)
    _setup_telemetry(app)
    return app


app = create_app()
