# TaskFlow — Docker Capstone Project

A task-management API platform built to mirror how a real platform/DevOps team
would containerize and ship a multi-tier application — reverse proxy, API,
database, cache, centralized logging, and metrics, all isolated across proper
network boundaries.

This project was built deliberately "wrong first, then fixed" at each stage —
the goal was to feel each problem (bloated images, broken cache, data loss,
open networks) before applying the fix, not just copy working config.

## Architecture (target end state)

- **Nginx** — reverse proxy, TLS termination
- **Flask API** — the core service, multi-stage Docker build
- **PostgreSQL** — primary data store, named volume for persistence
- **Redis** — cache/session store, named volume + AOF persistence
- **Fluent Bit → OpenSearch** — centralized log shipping
- **Prometheus + Grafana** — container metrics and dashboards
- **(optional) Kafka** — async messaging between services
- Three isolated Docker networks: `frontend-net`, `backend-net`, `monitoring-net`

## Progress

### ✅ Phase 0 — Project scaffolding
Per-service directories, each with its own build context, so building one
image never has access to another service's files. Git-tracked from commit 1.

### ✅ Phase 1 — API image: multi-stage Docker build
- Built a deliberately bad image first: `python:3.12` full base, no
  `.dockerignore`, broken layer-cache ordering, running as root — **1.12GB**.
- Diagnosed and fixed all four problems: `python:3.12-slim` base, proper
  `.dockerignore`, dependencies copied (and installed) before source code so
  code edits don't bust the pip-install cache, non-root user, gunicorn as the
  production WSGI server instead of Flask's dev server — **134MB (-88%)**.
- Caught and fixed a real bug along the way: a rebuilt image was still
  launching Flask's dev server instead of gunicorn; diagnosed with
  `docker inspect --format='{{.Config.Cmd}}'` instead of guessing, traced it
  to a stale `CMD` line, fixed, rebuilt, reverified.

### ✅ Phase 2 — Data persistence with named volumes
- Proved a container's filesystem dies with the container (ran Postgres with
  no volume, killed it, data gone).
- Proved a named volume decouples data lifetime from container lifetime (new
  container, same volume, same data — survives `docker rm`).
- Proved the volume itself is the actual thing worth protecting — deleting
  the volume destroys the data even with a fresh container attached.
- Repeated for Redis, plus the extra nuance that Redis needs
  `--appendonly yes` to actually persist writes to disk, since it's an
  in-memory store by default.

### ✅ Phase 3 — Network segmentation
- Created two isolated Docker networks: `frontend-net` and `backend-net`.
- Placed Postgres and Redis on `backend-net` only; placed Nginx on
  `frontend-net` only. Proved with a real failed connection (not just
  config review) that Nginx has **no route at all** to Postgres — Docker's
  embedded DNS can't even resolve the name across networks it isn't on,
  which is a stronger guarantee than a firewall rule blocking traffic.
- Connected the API container to both networks (`docker network connect`),
  making it the single intentional bridge between the untrusted edge and
  the data layer — verified end-to-end with a 4-way connectivity matrix:
  API→Postgres ✅, API→Redis ✅, Nginx→API ✅, Nginx→Postgres ❌.
- Learned that minimal images (from Phase 1's `slim` base) lack debug tools
  like `ping` by design, and the professional fix is a disposable, fully
  loaded debug container (`nicolaka/netshoot`) attached to the network under
  test — not bloating the production image with tools it doesn't need.

### ✅ Phase 4 — Nginx reverse proxy
- Replaced Nginx's default config with a real `upstream` + `proxy_pass` setup
  routing traffic to the API container by container name over `frontend-net`.
- Forwarded original client headers (`Host`, `X-Real-IP`,
  `X-Forwarded-For/Proto`) so the API never loses the real caller's identity
  behind the proxy hop.
- Confirmed the API has zero direct host port exposure — Nginx is the sole
  entry point into the whole stack.

### ✅ Phase 5 — Centralized logging: Fluent Bit → OpenSearch
- Ran OpenSearch single-node, handling the 2.12+ mandatory admin-password
  requirement and self-signed TLS rather than an outdated "disable security"
  approach.
- Built a Fluent Bit config that tails Docker's JSON log files directly via a
  bind mount (`/var/lib/docker/containers`, read-only), parses Docker's log
  wrapper format, and ships structured documents to OpenSearch.
- Verified end-to-end across all three layers — source logs, Fluent Bit's own
  processing logs, and real queryable documents landing in OpenSearch (not
  just "the container didn't crash").

### ⏭ Phase 6 — Metrics: cAdvisor + Prometheus + Grafana (next)
Per-container CPU/memory/network metrics scraped by Prometheus, visualized in
Grafana dashboards — the metrics counterpart to Phase 5's logging pipeline.

## Tech stack
Docker, Docker Compose, Python/Flask, gunicorn, PostgreSQL, Redis, Nginx,
Fluent Bit, OpenSearch, Prometheus, Grafana

## Why this project
Built as hands-on preparation for DevOps/Cloud Engineer roles — every phase
is designed to reproduce a real failure mode first (oversized images, cache
misses, data loss, flat networks) before fixing it, rather than starting from
a known-good config.
