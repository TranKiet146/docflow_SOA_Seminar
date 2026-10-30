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

Planning and architecture design.
