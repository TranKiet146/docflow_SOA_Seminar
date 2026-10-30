import os
import socket
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import json
from fastapi.responses import FileResponse

from fastapi import FastAPI, HTTPException, UploadFile, status
from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.tasks import process_document


SERVICE_NAME = os.getenv("SERVICE_NAME", "docflow-api")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "document-jobs")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))
RESULT_DIR = Path(os.getenv("RESULT_DIR", "/data/results"))

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "2"))
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "60"))
RESULT_TTL_SECONDS = int(os.getenv("RESULT_TTL_SECONDS", "86400"))

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".txt", ".md"}

async_redis_client: AsyncRedis | None = None
sync_redis_client: SyncRedis | None = None
job_queue: Queue | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global async_redis_client
    global sync_redis_client
    global job_queue

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    async_redis_client = AsyncRedis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )

    sync_redis_client = SyncRedis.from_url(
        REDIS_URL,
        decode_responses=False,
        socket_connect_timeout=2,
        socket_timeout=2,
    )

    job_queue = Queue(
        name=QUEUE_NAME,
        connection=sync_redis_client,
        default_timeout=JOB_TIMEOUT_SECONDS,
    )

    yield

    if async_redis_client is not None:
        await async_redis_client.aclose()

    if sync_redis_client is not None:
        sync_redis_client.close()

    async_redis_client = None
    sync_redis_client = None
    job_queue = None


app = FastAPI(
    title="DocFlow API",
    version="0.4.0",
    description="Asynchronous document processing API",
    lifespan=lifespan,
)


def require_queue() -> Queue:
    if job_queue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job queue has not been initialized",
        )

    return job_queue


def require_sync_redis() -> SyncRedis:
    if sync_redis_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis client has not been initialized",
        )

    return sync_redis_client

def fetch_job_or_404(job_id: str) -> Job:
    connection = require_sync_redis()

    try:
        return Job.fetch(job_id, connection=connection)
    except NoSuchJobError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        ) from exc
def normalize_job_status(job: Job) -> str:
    current_status = job.get_status(refresh=True)

    if hasattr(current_status, "value"):
        return current_status.value

    return str(current_status)


@app.get("/health/live")
async def liveness():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
    }


@app.get("/health/ready")
async def readiness():
    if async_redis_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis client has not been initialized",
        )

    try:
        redis_ready = await async_redis_client.ping()
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis unavailable: {exc}",
        ) from exc

    if not redis_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
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
        "version": "0.4.0",
        "hostname": socket.gethostname(),
        "runtime": "Python / FastAPI",
        "redis_url": REDIS_URL,
        "queue": QUEUE_NAME,
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "max_upload_mb": MAX_UPLOAD_MB,
    }


@app.post(
    "/api/jobs",
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_job(file: UploadFile):
    original_filename = Path(file.filename or "document").name
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        await file.close()

        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported file type. "
                f"Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )

    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_UPLOAD_MB} MB limit",
        )

    current_queue = require_queue()

    job_id = uuid.uuid4().hex
    stored_filename = f"{job_id}{extension}"
    stored_path = UPLOAD_DIR / stored_filename

    try:
        stored_path.write_bytes(content)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store uploaded document",
        ) from exc

    try:
        job = current_queue.enqueue(
            process_document,
            job_id,
            str(stored_path),
            original_filename,
            job_id=job_id,
            job_timeout=JOB_TIMEOUT_SECONDS,
            result_ttl=RESULT_TTL_SECONDS,
            failure_ttl=RESULT_TTL_SECONDS,
            meta={
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "size_bytes": len(content),
            },
        )
    except Exception as exc:
        stored_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not enqueue document processing job",
        ) from exc

    return {
        "job_id": job.id,
        "status": normalize_job_status(job),
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "size_bytes": len(content),
        "status_url": f"/api/jobs/{job.id}",
    }


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):

    job = fetch_job_or_404(job_id)

    job_status = normalize_job_status(job)

    response = {
        "job_id": job.id,
        "status": job_status,
        "meta": job.meta,
        "result": None,
        "error": None,
    }

    if job_status == "finished":
        response["result"] = job.result

    if job_status == "failed":
        response["error"] = "Document processing failed"

    return response
@app.get("/api/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    job = fetch_job_or_404(job_id)
    job_status = normalize_job_status(job)

    if job_status != "finished":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not finished. Current status: {job_status}",
        )

    result_path = RESULT_DIR / f"{job_id}.json"

    if not result_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated JSON report was not found",
        )

    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Generated JSON report could not be read",
        ) from exc


@app.get("/api/jobs/{job_id}/download")
async def download_job_report(job_id: str):
    job = fetch_job_or_404(job_id)
    job_status = normalize_job_status(job)

    if job_status != "finished":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not finished. Current status: {job_status}",
        )

    report_path = RESULT_DIR / f"{job_id}.html"

    if not report_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated HTML report was not found",
        )

    return FileResponse(
        path=report_path,
        media_type="text/html",
        filename=f"{job_id}-report.html",
    )