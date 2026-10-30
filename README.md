# docflow_SOA_Seminar

Docker Compose - Multi-container deployment - Environment configuration - Networking

# DocFlow
```markdown
[![DocFlow CI](https://github.com/TranKiet146/docflow_SOA_Seminar/actions/workflows/ci.yml/badge.svg)](https://github.com/TranKiet146/docflow_SOA_Seminar/actions/workflows/ci.yml)

DocFlow is an asynchronous document processing application used to demonstrate:

- Docker Compose multi-container deployment
- Environment configuration
- Docker networking and service discovery
- Background job processing
- Persistent volumes
- Health checks and failure recovery

## Use case

A user uploads a TXT or Markdown document. The API queues a background job.
A worker processes the document and generates a report containing word count,
line count, reading time, frequent terms and SHA-256 checksum.

## Planned services

- Nginx gateway
- FastAPI application
- Redis Queue
- Document worker

## Project status

Milestone 3 completed:

- FastAPI accepts TXT and Markdown uploads
- Redis Queue stores asynchronous jobs
- A dedicated Worker processes queued documents
- API and Worker use the same backend image with different commands
- Generated JSON and HTML reports are stored in a named volume
- Worker failure recovery and horizontal scaling are supported
  Planning and architecture design.

## Project status

## Automated verification

Run the end-to-end smoke test:

```bash
docker compose --profile test run --rm smoke-test

Run Worker recovery verification on Windows:
powershell -ExecutionPolicy Bypass -File .\scripts\test-recovery.ps1

Run Redis recovery verification:
powershell -ExecutionPolicy Bypass -File .\scripts\test-redis-recovery.ps1

Project status
Milestone 6 in progress:
- Multi-container deployment is operational
- Nginx is the only public entry point
- API, Redis Queue and Worker are network-isolated
- Document processing generates JSON and HTML reports
- End-to-end integration testing is automated
- Worker and Redis recovery scenarios are verified
- GitHub Actions CI validates every push and pull request
