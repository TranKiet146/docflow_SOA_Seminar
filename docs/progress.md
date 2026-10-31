# DocFlow project progress

Last updated: 2026-10-31

## Completed milestones

### Milestone 1 — Foundation

- Repository structure
- FastAPI backend
- Docker image
- Docker Compose foundation
- Environment configuration

### Milestone 2 — Upload and queue

- TXT and Markdown uploads
- Upload validation
- Persistent document volume
- Redis Queue integration
- Asynchronous job identifiers and status

### Milestone 3 — Worker and reports

- Dedicated RQ Worker
- JSON document reports
- HTML report downloads
- Worker horizontal scaling
- Queued-job recovery

### Milestone 4 — Gateway and web interface

- Nginx reverse proxy
- Browser upload interface
- Gateway as the only published service
- edge-net and internal job-net
- Docker DNS service discovery

### Milestone 5 — Automated verification

- Containerized end-to-end smoke test
- Invalid upload validation
- JSON and HTML report verification
- Worker outage recovery test
- Redis outage and readiness recovery test

### Milestone 6 — Continuous integration

- GitHub Actions workflow
- Compose configuration validation
- Automated image builds
- Gateway health verification
- End-to-end smoke testing on Ubuntu
- Failure logs and automatic cleanup

## Confirmed architecture

Browser → Nginx Gateway → FastAPI → Redis Queue → Worker

The API and Worker share a named volume for uploaded documents and
generated reports.

Only Nginx publishes a host port.

## Development environment

- Windows
- PowerShell
- Docker Desktop
- Visual Studio Code
- Localhost is the primary seminar demonstration environment

## Important implementation decisions

- FastAPI is not published directly to the host.
- Redis and Worker are isolated from edge-net.
- RQ uses a Redis client with decode_responses disabled.
- Gateway health checks use 127.0.0.1 instead of localhost.
- The integration test is tests/tests.py.
- Recovery scripts restore stopped services through finally blocks.

## Next milestones

1. Architecture and seminar documentation
2. Presentation content and diagrams
3. Expected reviewer questions and answers
4. Final rehearsal and release tag
