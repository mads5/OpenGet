import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import repos, contributors, pools, payouts

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    try:
        from app.core.redis import close_redis
        await close_redis()
    except Exception:
        pass


app = FastAPI(
    title="OpenGet API",
    description="Reward open-source contributors from a community-funded pool",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"https://[\w\-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    detail = str(exc)
    if hasattr(exc, "message"):
        detail = exc.message
    return JSONResponse(status_code=500, content={"detail": detail})


app.include_router(repos.router, prefix="/api/v1")
app.include_router(contributors.router, prefix="/api/v1")
app.include_router(pools.router, prefix="/api/v1")
app.include_router(payouts.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "openget-backend"}
