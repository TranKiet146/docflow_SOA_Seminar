import json
import os
import socket
import sys
import time
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = os.getenv(
    "BASE_URL",
    "http://localhost:8080",
).rstrip("/")

EXPECTED_API_VERSION = os.getenv(
    "EXPECTED_API_VERSION",
    "0.5.0",
)

POLL_TIMEOUT_SECONDS = int(
    os.getenv("POLL_TIMEOUT_SECONDS", "60")
)

REQUEST_TIMEOUT_SECONDS = 10


def log(message: str) -> None:
    print(f"[smoke-test] {message}", flush=True)


def request(
    path: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    expected_status: int = 200,
) -> tuple[bytes, dict[str, str]]:
    http_request = Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers or {},
        method=method,
    )

    try:
        with urlopen(
            http_request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            status_code = response.status
            response_body = response.read()
            response_headers = dict(response.headers.items())
    except HTTPError as exc:
        status_code = exc.code
        response_body = exc.read()
        response_headers = dict(exc.headers.items())

    if status_code != expected_status:
        preview = response_body.decode(
            "utf-8",
            errors="replace",
        )

        raise AssertionError(
            f"{method} {path} returned {status_code}; "
            f"expected {expected_status}. Body: {preview}"
        )

    return response_body, response_headers


def request_json(
    path: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    expected_status: int = 200,
) -> dict:
    response_body, _ = request(
        path,
        method=method,
        body=body,
        headers=headers,
        expected_status=expected_status,
    )

    return json.loads(response_body.decode("utf-8"))


def multipart_document(
    filename: str,
    content: bytes,
) -> tuple[bytes, str]:
    boundary = f"docflow-{uuid.uuid4().hex}"

    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            (
                "Content-Disposition: form-data; "
                f'name="file"; filename="{filename}"\r\n'
            ).encode(),
            b"Content-Type: text/plain\r\n\r\n",
            content,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )

    return (
        body,
        f"multipart/form-data; boundary={boundary}",
    )


def upload_document(
    filename: str,
    content: bytes,
    *,
    expected_status: int,
) -> dict:
    body, content_type = multipart_document(
        filename,
        content,
    )

    return request_json(
        "/api/jobs",
        method="POST",
        body=body,
        headers={
            "Content-Type": content_type,
        },
        expected_status=expected_status,
    )


def wait_for_job(job_id: str) -> dict:
    deadline = (
        time.monotonic() + POLL_TIMEOUT_SECONDS
    )

    last_status = None

    while time.monotonic() < deadline:
        job = request_json(
            f"/api/jobs/{job_id}"
        )

        current_status = job["status"]

        if current_status != last_status:
            log(
                f"job {job_id}: {current_status}"
            )
            last_status = current_status

        if current_status == "finished":
            return job

        if current_status == "failed":
            raise AssertionError(
                f"Job failed: {job}"
            )

        time.sleep(1)

    raise TimeoutError(
        f"Job {job_id} did not finish within "
        f"{POLL_TIMEOUT_SECONDS} seconds"
    )


def run() -> None:
    log(f"testing {BASE_URL}")

    health_body, _ = request("/health")

    health_text = health_body.decode(
        "utf-8",
        errors="replace",
    ).strip()

    if health_text != "gateway ok":
        raise AssertionError(
            "Unexpected Gateway health response: "
            f"{health_text!r}"
        )

    log("PASS gateway health")

    info = request_json("/api/info")

    assert info["service"] == "docflow-api"
    assert info["version"] == EXPECTED_API_VERSION

    log("PASS API information through Nginx")

    try:
        socket.gethostbyname("redis")
    except socket.gaierror:
        log("PASS Redis is isolated from edge-net")
    else:
        raise AssertionError(
            "Redis unexpectedly resolved from edge-net"
        )

    invalid = upload_document(
        "unsafe.exe",
        b"not an executable",
        expected_status=415,
    )

    assert (
        "Unsupported file type"
        in invalid["detail"]
    )

    log("PASS unsupported upload rejected")

    content = (
        b"# DocFlow integration test\n\n"
        b"Redis queues jobs and the Worker "
        b"processes jobs.\n"
    )

    accepted = upload_document(
        "integration-test.md",
        content,
        expected_status=202,
    )

    assert accepted["status"] in {
        "queued",
        "started",
    }

    job_id = accepted["job_id"]

    log(
        f"PASS upload accepted as job {job_id}"
    )

    wait_for_job(job_id)

    log("PASS Worker completed queued job")

    result = request_json(
        f"/api/jobs/{job_id}/result"
    )

    assert result["job_id"] == job_id

    assert (
        result["original_filename"]
        == "integration-test.md"
    )

    assert result["word_count"] == 11
    assert result["line_count"] == 3
    assert len(result["sha256"]) == 64

    log("PASS JSON report contents")

    html_report, headers = request(
        f"/api/jobs/{job_id}/download"
    )

    assert (
        b"DocFlow document report"
        in html_report
    )

    assert (
        "text/html"
        in headers.get("Content-Type", "")
    )

    log("PASS HTML report download")
    log("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(
            f"[smoke-test] FAILED: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(1) from exc