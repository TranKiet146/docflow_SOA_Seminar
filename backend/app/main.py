import os
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from redis.asyncio import Redis
from redis.exceptions import RedisError


SERVICE_NAME = os.getenv("SERVICE_NAME", "docflow-api")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "document-jobs")

redis_client: Redis | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global redis_client

    redis_client = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )

    yield

    if redis_client is not None:
        await redis_client.aclose()

    redis_client = None


app = FastAPI(
    title="DocFlow API",
    version="0.1.0",
    description="Asynchronous document processing API",
    lifespan=lifespan,
)


@app.get("/health/live")
async def liveness():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
    }


@app.get("/health/ready")
async def readiness():
    if redis_client is None:
        raise HTTPException(
            status_code=503,
            detail="Redis client has not been initialized",
        )

    try:
        redis_ready = await redis_client.ping()
    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Redis unavailable: {exc}",
        ) from exc

    if not redis_ready:
        raise HTTPException(
            status_code=503,
            detail="Redis did not respond successfully",
        )

    return {
        "status": "ready",
        "service": SERVICE_NAME,
        "dependencies": {
            "redis": "ok",
        },
    }


@app.get("/api/info")
async def service_info():
    return {
        "service": SERVICE_NAME,
        "version": "0.1.0",
        "hostname": socket.gethostname(),
        "runtime": "Python / FastAPI",
        "redis_url": REDIS_URL,
        "queue": QUEUE_NAME,
    }