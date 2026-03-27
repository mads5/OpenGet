from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.redis import close_redis
from app.routers import projects, rankings, pools, payouts


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="OSSPool API",
    description="Open-source project funding platform with quadratic funding",
    version="0.1.0",
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

app.include_router(projects.router, prefix="/api/v1")
app.include_router(rankings.router, prefix="/api/v1")
app.include_router(pools.router, prefix="/api/v1")
app.include_router(payouts.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "osspool-backend"}
