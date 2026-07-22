# SentryOps

> Kubernetes observability and AI SRE platform — logs, metrics, traces, events, dashboards, and an autonomous LangGraph agent that investigates and remediates incidents.

---

## Architecture

### System Overview

![SentryOps Architecture](docs/architecture.png)

| Zone | Components |
|---|---|
| **Frontend** | Next.js 16 on `:3000` — cluster, pods, nodes, logs, metrics, traces, events, Guardian, dashboards, AI chat |
| **Backend API** | FastAPI on `:8000` — REST, WebSocket, SSE endpoints. Python 3.13 / uvicorn |
| **Background Workers** | Log Collector, Metrics Collector, Prometheus Scraper, Event Collector, Resource Snapshotter, Guardian Scheduler — all launched at startup |
| **Kubernetes** | CoreV1 + AppsV1 + Metrics Server via kubeconfig. Client singletons initialized at import |
| **OTel Receiver** | OTLP gRPC on `:4317` — accepts spans from instrumented apps, writes to ClickHouse |
| **Storage** | PostgreSQL (relational state) · ClickHouse (time-series: logs, metrics, traces, events, deploys) · Redis (pub/sub, log streaming, cache) |
| **AI Layer** | LangChain + LangGraph for AI chat agent and Guardian investigations → AWS Bedrock (Claude) + Langfuse tracing |
| **GitHub Integration** | GitHub App — webhooks, deploy detector, fix generator, PR creation |

### Backend Internals

![Backend Internals](docs/arch-backend.png)

The FastAPI backend is organized into three layers: **API Routers** (thin handlers), **Services** (business logic), and **Core** (k8s client singletons + config). Four background workers start alongside the API process and write collected data directly into ClickHouse and Redis.

### Observability Data Pipeline

![Observability Data Pipeline](docs/arch-data-pipeline.png)

Three parallel pipelines ingest observability signals into ClickHouse: logs via a collector/ingester queue, metrics via Prometheus scraping + Kubernetes metrics-server polling, and traces/events via the OTLP gRPC receiver and Kubernetes event watch respectively.

### Guardian — AI SRE Agent Flow

![Guardian Agent Flow](docs/arch-guardian.png)

Guardian is a LangGraph state machine that detects anomalies, gathers evidence, analyzes root causes via AWS Bedrock, proposes remediations, waits for human approval, and then executes against the Kubernetes API — with automatic post-action verification.

### GitHub Integration

![GitHub Integration](docs/arch-github.png)

Two complementary flows: inbound webhook events (deployment status, push, pull_request) drive deploy correlation and Guardian triggers; outbound fix generation uses the GitHub App to produce AI-authored patches and open pull requests automatically.

---

## Features

**Cluster Visibility**
- Live view of pods, nodes, namespaces, and deployments from the Kubernetes API
- Per-pod detail: containers, resource usage, events, metadata

**Log Management**
- Continuous log collection from all pod containers → ClickHouse
- Full-text search with filters (namespace, pod, container, level, time range)
- Live WebSocket log streaming per pod/container
- Log volume histograms by severity level

**Metrics**
- Prometheus scraping + Kubernetes metrics-server polling → ClickHouse
- Per-pod and per-node CPU/memory time-series queries
- Configurable `step` and `group_by` for aggregation
- Custom dashboards with stat cards, metric charts, log tables, and event lists

**Distributed Tracing**
- OTLP gRPC receiver on port `4317` for OpenTelemetry spans
- Trace search by service, operation, duration, and status
- Waterfall view with span detail panel
- Service map: span count, error rate, p95 latency per service

**Kubernetes Events**
- Continuous event watch → ClickHouse
- Warning vs normal volume over time
- Events correlated to involved objects
- SSE real-time event stream

**Resource Change Tracking**
- Snapshots of Kubernetes resources → ClickHouse
- Change history per resource (namespace/kind/name)
- Hourly change timeline and summary

**Deployment History**
- Deployment timeline correlated with incidents
- Per-deployment verification checks and impact metrics
- GitHub deploy correlation via webhook events

**Guardian — AI SRE Agent**
- Autonomous LangGraph agent that detects anomalies, investigates root causes, and proposes (or executes) remediations
- Human-in-the-loop approval flow before any destructive action
- Configurable auto-rollback mode

**AI Chat**
- Streaming SSE chat powered by LangChain + AWS Bedrock
- Context-aware: has tools to query logs, metrics, traces, and Kubernetes state
- Session history persisted per session ID

**GitHub Integration**
- GitHub App authentication (JWT + installation tokens)
- Webhook handler for `deployment_status`, `push`, `pull_request`
- Deploy detector correlates Kubernetes image changes to GitHub commits
- Fix generator creates AI-authored PRs for failing deployments

**Alerting**
- AI-suggested alerts surfaced from observability data
- Accept/dismiss workflow for alert suggestions

**Notifications**
- Slack webhook notifications for alerts and Guardian actions
- Generic outbound webhooks for external integrations
- In-app notification feed with rate limiting

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| UI Components | shadcn/ui, Lucide icons, TanStack Table, Recharts |
| Backend | FastAPI, Python 3.13, uvicorn, Pydantic v2 |
| Kubernetes | `kubernetes` Python client (CoreV1, AppsV1, CustomObjects/metrics) |
| Relational DB | PostgreSQL 16 via SQLAlchemy async + asyncpg |
| Time-series DB | ClickHouse 24 via clickhouse-connect |
| Cache / Pub-Sub | Redis 7 via redis-py with hiredis |
| AI Orchestration | LangChain ≥1.3, LangGraph ≥1.2 |
| LLM | AWS Bedrock (Claude) via langchain-aws + boto3 |
| LLM Observability | Langfuse ≥4.0 |
| Distributed Tracing | OpenTelemetry — OTLP gRPC receiver (grpcio) |
| GitHub | PyGithub, PyJWT, cryptography |
| Package Manager | uv (backend), npm (frontend) |
| Local K8s | Kind with 1 control-plane + 2 worker nodes |

---

## Prerequisites

- Python 3.13+
- Node.js 20+ and npm
- [uv](https://github.com/astral-sh/uv) — Python package manager
- Docker + Docker Compose (for PostgreSQL, ClickHouse, Redis)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) and [kind](https://kind.sigs.k8s.io/) for local Kubernetes
- A valid `kubeconfig` with an active context (the backend loads it at startup)
- AWS account with Bedrock access enabled (for AI features)

---

## Quick Start

### 1. Start infrastructure

```bash
docker compose up -d
```

This starts PostgreSQL on `:5432`, ClickHouse on `:8123`/`:9000`, and Redis on `:6379`.

### 2. Backend

```bash
cd backend
uv sync
cp .env.example .env      # edit with your values — see Environment Variables below
uv run uvicorn main:app --reload --port 8000
```

The backend runs ClickHouse migrations automatically on startup. Background workers (log collector, metrics collector, event collector, Guardian scheduler) start alongside the API.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev               # http://localhost:3000
```

### 4. Local Kubernetes cluster (Kind)

```bash
kind create cluster --config setup/kind-config.yaml   # 1 control-plane + 2 workers, k8s 1.30
kubectl apply -f setup/sample-workloads.yaml          # deploy demo workloads in 'demo' namespace
kubectl config use-context kind-sentryops
```

---

## Environment Variables

Create `backend/.env` with the following. All values have defaults except AWS credentials and GitHub App config.

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `False` | Enable debug mode |
| `DATABASE_URL` | `postgresql+asyncpg://sentryops:sentryops@localhost:5432/sentryops` | PostgreSQL async connection string |
| `CLICKHOUSE_HOST` | `localhost` | ClickHouse host |
| `CLICKHOUSE_PORT` | `8123` | ClickHouse HTTP port |
| `CLICKHOUSE_USER` | `default` | ClickHouse user |
| `CLICKHOUSE_PASSWORD` | `""` | ClickHouse password |
| `CLICKHOUSE_DATABASE` | `sentryops` | ClickHouse database name |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `AWS_ACCESS_KEY_ID` | — | AWS credentials for Bedrock |
| `AWS_SECRET_ACCESS_KEY` | — | AWS credentials for Bedrock |
| `AWS_REGION` | `us-east-1` | AWS region |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Bedrock model used for AI chat and Guardian |
| `LANGFUSE_PUBLIC_KEY` | — | Langfuse public key (optional) |
| `LANGFUSE_SECRET_KEY` | — | Langfuse secret key (optional) |
| `LANGFUSE_BASE_URL` | `https://cloud.langfuse.com` | Langfuse endpoint |
| `OTLP_GRPC_PORT` | `4317` | Port for OTLP gRPC receiver |
| `PROMETHEUS_SCRAPE_INTERVAL` | `30` | Seconds between Prometheus scrapes |
| `K8S_CONTEXT` | `None` | Override active kubeconfig context |
| `CORS_ORIGIN` | `["http://localhost:3000"]` | Allowed CORS origins |
| `GITHUB_APP_ID` | — | GitHub App ID |
| `GITHUB_APP_PRIVATE_KEY` | — | GitHub App private key (PEM string) |
| `GITHUB_WEBHOOK_SECRET` | — | HMAC secret for webhook verification |
| `GITHUB_CLIENT_ID` | — | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | — | GitHub OAuth client secret |
| `GUARDIAN_AUTO_ROLLBACK_ENABLED` | `False` | Allow Guardian to rollback without human approval |
| `DEPLOY_VERIFICATION_ENABLED` | `True` | Run post-deploy health checks |
| `FRONTEND_URL` | `http://localhost:3000` | Used for CORS and generated links |

Frontend variable (set in `frontend/.env.local`):

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## API Reference

### Cluster & Resources

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/cluster/summary` | Cluster-wide summary |
| `GET` | `/api/v1/pods` | List all pods |
| `GET` | `/api/v1/pods/{namespace}/{name}` | Pod detail |
| `GET` | `/api/v1/pods/{namespace}/{name}/events` | Pod events |
| `GET` | `/api/v1/nodes` | List all nodes |
| `GET` | `/api/v1/namespaces` | List all namespaces |
| `GET` | `/api/v1/deployments` | List all deployments |
| `GET` | `/api/v1/deployments/{namespace}/{name}` | Deployment detail |

### Logs

| Method | Path | Query Params |
|---|---|---|
| `GET` | `/api/v1/logs` | `q`, `namespace`, `pod`, `container`, `level`, `since`, `until`, `limit`, `direction` |
| `GET` | `/api/v1/logs/stats` | Log volume by level over time |
| `WS` | `/ws/logs` | Live log stream (`namespace`, `pod`, `container`, `level`) |

### Metrics

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/metrics/pods` | Live pod CPU/memory from metrics-server |
| `GET` | `/api/v1/metrics/query` | Time-series query (`metric`, `namespace`, `pod`, `node`, `since`, `until`, `step`, `group_by`) |
| `GET` | `/api/v1/metrics/summary` | Top 10 CPU and memory pods |
| `GET` | `/api/v1/metrics/pod/{namespace}/{name}` | Per-pod metric series |

### Events

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/events` | List events with filters |
| `GET` | `/api/v1/events/stats` | Event volume (warning vs normal) over time |
| `GET` | `/api/v1/events/correlated` | Events grouped by involved object |
| `GET` | `/api/v1/events/stream` | SSE real-time event stream |

### Traces

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/traces` | Search traces (`service`, `operation`, `min/max_duration_ms`, `status`, `since`, `limit`) |
| `GET` | `/api/v1/traces/services` | Services with span count, error rate, p95 latency |
| `GET` | `/api/v1/traces/services/{service}/operations` | Operations for a service |
| `GET` | `/api/v1/traces/{trace_id}` | Full trace with all spans |

### AI Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/ai/chat` | Streaming SSE chat with LangChain agent |
| `GET` | `/api/v1/ai/sessions/{session_id}` | Fetch session history |
| `DELETE` | `/api/v1/ai/sessions/{session_id}` | Clear session |

### Guardian

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/guardian/investigations` | List investigations |
| `GET` | `/api/v1/guardian/investigations/{id}` | Investigation detail (evidence, root causes, remediations) |
| `POST` | `/api/v1/guardian/investigations` | Trigger manual investigation |
| `POST` | `/api/v1/guardian/investigations/{id}/approve` | Approve or reject remediation |
| `GET` | `/api/v1/guardian/status` | Guardian scheduler status |
| `GET` | `/api/v1/guardian/approvals` | List pending approvals |
| `GET` | `/api/v1/guardian/approvals/count` | Pending approval count |
| `POST` | `/api/v1/guardian/approvals/{id}/approve` | Approve |
| `POST` | `/api/v1/guardian/approvals/{id}/reject` | Reject |

### Changes, Deploys, Dashboards, Alerts

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/changes` | Resource change list |
| `GET` | `/api/v1/changes/summary` | Change summary + hourly timeline |
| `GET` | `/api/v1/changes/resource/{namespace}/{kind}/{name}` | Per-resource change history |
| `GET` | `/api/v1/deploys` | Deployment list |
| `GET` | `/api/v1/deploys/{id}` | Deployment detail with verification and impact metrics |
| `GET` | `/api/v1/deploys/timeline` | Deployment + incident timeline |
| `GET/POST` | `/api/v1/dashboards` | List / create dashboards |
| `GET/PUT/DELETE` | `/api/v1/dashboards/{id}` | Get / update / delete dashboard |
| `POST` | `/api/v1/dashboards/panels/query` | Execute panel query |
| `GET` | `/api/v1/alerts/suggestions` | AI-suggested alerts |
| `POST` | `/api/v1/alerts/suggestions/{id}/accept` | Accept suggestion |
| `POST` | `/api/v1/alerts/suggestions/{id}/dismiss` | Dismiss suggestion |
| `GET` | `/api/v1/correlate/trace/{trace_id}` | Cross-signal correlation by trace |
| `GET` | `/api/v1/correlate/resource/{namespace}/{pod}` | Cross-signal correlation by pod |
| `POST` | `/webhooks/github` | GitHub webhook receiver |

---

## Guardian — AI SRE Agent

![Guardian Agent Flow](docs/arch-guardian.png)

Guardian is an autonomous SRE agent built on LangGraph. It runs on a configurable schedule, detects anomalies across logs/metrics/events, and drives investigations through a multi-node graph:

```
gather → analyze → decide_remediation → [human approval] → execute
```

- **gather**: Collects logs, metrics, events, and Kubernetes state for the affected resource
- **analyze**: Uses AWS Bedrock (Claude) to identify root causes and classify severity
- **decide_remediation**: Proposes concrete actions (restart pod, scale deployment, rollback)
- **await_approval**: Pauses the graph and creates an approval notification — a human must accept or reject via the API or UI before execution proceeds
- **execute**: Applies the approved action against the Kubernetes API (includes rollback capability)

Set `GUARDIAN_AUTO_ROLLBACK_ENABLED=true` to skip the approval step (not recommended for production).

---

## GitHub Integration

![GitHub Integration](docs/arch-github.png)

Requires a GitHub App installed on your repository. Set the four `GITHUB_*` environment variables.

- **Webhook handler** (`POST /webhooks/github`): Receives `deployment_status`, `push`, and `pull_request` events. HMAC-verified using `GITHUB_WEBHOOK_SECRET`.
- **Deploy detector**: Watches for Kubernetes image changes and correlates them to GitHub commits and pull requests.
- **Fix generator**: When a deployment fails verification, Guardian can invoke the fix generator to produce an AI-authored diff and open a pull request on the repository.
- **Git context**: Provides Guardian and the AI chat agent with commit history, file diffs, and PR context for root-cause analysis.

---

## OpenTelemetry / Distributed Traces

SentryOps includes a built-in OTLP gRPC receiver. Point your instrumented services at:

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Spans are ingested into ClickHouse via `otel/trace_processor.py` and are immediately queryable through the traces API and the Traces UI. Metrics sent over OTLP are handled by `otel/metric_processor.py` and stored alongside Prometheus-scraped metrics.

---

## Sample Workloads

The `setup/sample-workloads.yaml` deploys five demo apps in the `demo` namespace to exercise the platform:

| Deployment | Behavior | What it tests |
|---|---|---|
| `nginx-healthy` | 3 replicas, stable | Baseline healthy pod visibility |
| `crashloop-app` | Crashes every 5 seconds | CrashLoopBackOff detection, log collection from short-lived containers |
| `memory-hog` | Allocates until OOM-killed | OOMKilled event detection, memory metrics alerting |
| `log-generator` | Emits structured JSON logs at high rate (2 replicas) | Log ingestion pipeline, search, and histogram |
| `slow-start` | 60-second readiness delay | Readiness probe failure events, Guardian detection |

---

## ClickHouse Schema

Six migrations under `backend/app/db/clickhouse/migrations/`:

| Migration | Table | Contents |
|---|---|---|
| `001_logs.sql` | `logs` | Pod log lines with level, timestamp, namespace, pod, container |
| `002_metrics.sql` | `metrics` | CPU/memory time-series per pod/node |
| `003_alerts.sql` | `alerts` | Alert events with severity and resource reference |
| `004_resource_change.sql` | `resource_changes` | Kubernetes resource snapshots and diffs |
| `005_traces.sql` | `traces` / `spans` | OTLP span data with service, operation, duration, status |
| `006_deployments.sql` | `deployments` / `deployment_verifications` / `deployment_impact` | Deploy history, verification results, impact metrics |

---

## Project Roadmap

| Phase | Status | Description |
|---|---|---|
| 1 | Done | Cluster connection — pods, nodes, namespaces, deployments |
| 2 | Done | Log collection — ClickHouse ingestion, search, WebSocket streaming |
| 3 | Done | Metrics + AI chat — Prometheus scraping, LangChain v1, AWS Bedrock, Langfuse |
| 4 | Done | Guardian AI SRE agent — LangGraph, anomaly detection, human-in-the-loop approvals |
| 5 | Done | Alerting + dashboards — alert suggestions, custom panel dashboards |
| 6 | Done | OTel tracing — OTLP gRPC receiver, trace search, waterfall, service map |
| 7 | Done | GitHub integration — webhooks, deploy detector, fix generator, PR creation |
| 8 | Planned | Multi-cluster support |
| 9 | Planned | MCP server — expose SentryOps tools to external AI agents |

---

## License

[MIT](LICENSE)
