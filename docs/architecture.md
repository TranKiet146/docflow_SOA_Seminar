# Architecture

Browser → Nginx → FastAPI → Redis Queue → Worker

The API and worker share a named volume containing uploaded files and reports.

## Networks

- edge-net: Nginx and API
- job-net: API, Worker and Redis

Only Nginx publishes a host port.
