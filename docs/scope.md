# Project Scope

## Core features

- Upload TXT and Markdown files
- Queue document processing jobs
- Track queued, processing, completed and failed states
- Generate HTML or JSON reports
- Download completed reports

## Technical objectives

- Run all services with Docker Compose
- Publish only the Nginx gateway port
- Separate edge and processing networks
- Persist Redis data and uploaded documents
- Demonstrate worker failure and recovery
- Demonstrate worker scaling

## Out of scope

- User authentication
- PDF and Office document parsing
- Multi-host deployment
- Kubernetes
- Production monitoring