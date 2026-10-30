# docflow_SOA_Seminar

Docker Compose - Multi-container deployment - Environment configuration - Networking

# DocFlow

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

Milestone 4 completed:

- Nginx is the only public entry point
- A browser UI uploads documents and displays job progress
- API requests are reverse-proxied to FastAPI by Docker service name
- FastAPI is reachable only through the internal Compose network
- Redis and Worker are isolated from the edge network
- Generated HTML reports can be downloaded from the UI
