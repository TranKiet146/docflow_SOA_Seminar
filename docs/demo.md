# DocFlow seminar demonstration

## Target duration

8–10 minutes.

## Preparation

Before presenting:

```powershell
docker compose down
docker compose up -d --build
docker compose ps
```

Confirm:

- Gateway is healthy
- API is healthy
- Redis is healthy
- Worker is running
- `http://localhost:8080` opens successfully

Keep these pages ready:

- DocFlow UI
- GitHub repository
- GitHub Actions
- PowerShell terminal
- Docker Desktop container view

## Demonstration sequence

### 1. Introduce the problem

Explain that document processing may take longer than a normal HTTP request.

Processing directly inside the API would:

- Keep the request open
- Reduce API throughput
- Couple user requests to processing availability
- Lose work more easily during failures

DocFlow solves this through an asynchronous queue.

### 2. Show the running services

```powershell
docker compose ps
```

Explain the four primary containers:

- Gateway
- API
- Redis
- Worker

Point out that only Gateway publishes a host port.

### 3. Show the browser flow

Open:

```text
http://localhost:8080
```

Upload a TXT or Markdown document.

Show:

1. Job creation
2. Queued or processing state
3. Finished state
4. Generated statistics
5. HTML report download

### 4. Explain the request path

Use the architecture diagram:

```text
Browser → Nginx → FastAPI → Redis Queue → Worker
```

Explain that API is the Producer, Redis is the Queue and Worker is the
Consumer.

### 5. Demonstrate network isolation

```powershell
docker compose exec gateway `
  wget -qO- http://api:8000/api/info
```

The request succeeds because Gateway and API share `edge-net`.

Then run:

```powershell
docker compose exec gateway getent hosts redis
```

No Redis address should be returned because Gateway is not connected to
`job-net`.

### 6. Demonstrate Worker recovery

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\test-recovery.ps1
```

Explain:

- API remains available
- Job remains queued
- No request data is lost
- Restarted Worker processes the existing job

### 7. Demonstrate scaling

```powershell
docker compose up -d --scale worker=3
docker compose ps
```

Explain that Workers do not publish ports and can be replicated without port
conflicts.

Return to one Worker:

```powershell
docker compose up -d --scale worker=1
```

### 8. Show automated testing

Open the GitHub Actions page and show the successful `DocFlow CI` workflow.

Explain that every push verifies:

- Compose configuration
- Image builds
- Container health
- Complete upload and processing path
- Generated reports

## Closing statement

DocFlow demonstrates that Docker Compose is not only a tool for starting
multiple containers. It defines service relationships, network boundaries,
persistent storage, health conditions, recovery behavior and repeatable
deployment.

## Backup plan

If the live upload fails:

1. Show the most recent successful GitHub Actions run.
2. Show the Worker recovery test output.
3. Open an existing generated HTML report.
4. Explain the architecture using the committed diagrams.

Do not delete Docker volumes immediately before the presentation.
