# LTA Bus Arrival Proxy — SRE Learning Project

A production-instrumented proxy over the [LTA DataMall Bus Arrival API](https://datamall.lta.gov.sg),
built as a portfolio SRE project demonstrating SLI definition, SLO tracking, burn rate alerting,
Grafana dashboarding, and cloud deployment.

---

## Versions

### v1 — Local Docker Compose

Run the full stack locally on your machine for development and learning.

```bash
docker compose up --build
```

Stack: FastAPI app + Prometheus + Alertmanager + Grafana + ELK (Elasticsearch, Logstash, Kibana) + React frontend

| Service | URL |
| --- | --- |
| React UI | <http://localhost:5173> |
| API | <http://localhost:8000> |
| Grafana | <http://localhost:3000> |
| Prometheus | <http://localhost:9090> |
| Alertmanager | <http://localhost:9093> |
| Kibana | <http://localhost:5601> |

---

### v2 — EC2 Docker Compose (current)

Deploy directly on an AWS EC2 t3.medium instance using Docker Compose.
No Kubernetes — simplest cloud deployment.

```bash
# On the EC2 server
git clone https://github.com/sparkling-snail/lta-proxy
cd lta-proxy
cp .env.example .env && nano .env
docker compose up -d --build
```

Live at: `http://<ec2-ip>:5173`

For a t3.micro (1GB RAM) use the prod compose without ELK:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

---

### v3 — EKS (coming next)

Deploy to AWS Elastic Kubernetes Service using Terraform + Helm.

- Terraform provisions VPC + EKS cluster + node group
- Kubernetes manifests for the app (Deployment, Service, HPA)
- kube-prometheus-stack via Helm (replaces Docker Compose observability)
- AWS Load Balancer Controller for public ingress
- GitHub Actions CI/CD pipeline

---

## Architecture

```text
Client → FastAPI Proxy → LTA DataMall API
              ↓
         Prometheus ← scrapes /metrics every 10s
              ↓
           Grafana (dashboards + SLO panels)
              ↓
        Alertmanager (burn rate alerts)
```

## Log pipeline

```text
app.py writes JSON logs to /app/logs/app.log
              ↕  (shared Docker volume: app_logs)
Logstash reads from /logs/app.log
  → parses JSON fields
  → tags slow requests, errors, cache misses
  → ships to Elasticsearch
              ↓
Elasticsearch stores as searchable documents (index: lta-proxy-YYYY.MM.DD)
              ↓
Kibana — search and visualise logs at http://localhost:5601
```

## SLOs defined

| SLO | Target | SLI |
| --- | ------ | --- |
| Availability | >= 99.5% | `successful_requests / total_requests` |
| P95 Latency | < 500ms | `histogram_quantile(0.95, ...)` |
| Data freshness | cache age < 30s | `lta_bus_arrival_cache_age_seconds` |

## Quick start (v1 local)

### 1. Get an LTA API key

Register at [datamall.lta.gov.sg](https://datamall.lta.gov.sg/content/datamall/en/request-for-api.html) (free, ~10 min).

### 2. Configure

```bash
cp .env.example .env
# edit .env and paste your key
```

### 3. Run

```bash
docker compose up --build
```

### 4. Verify

```bash
curl http://localhost:8000/arrivals/83139
curl http://localhost:8000/metrics | grep lta_
```

### 5. Open dashboards

- Grafana: <http://localhost:3000> (admin / admin)
- Prometheus: <http://localhost:9090>
- Alertmanager: <http://localhost:9093>
- Kibana: <http://localhost:5601>

## Quick start (v2 EC2)

### 1. Launch an EC2 instance

- OS: Ubuntu 24.04
- Instance type: t3.medium (4GB RAM, needed for ELK) or t3.micro (1GB, use prod compose)
- Storage: 20GB gp3
- Security group — open inbound ports: `22`, `8000`, `5173`, `3000`, `9090`, `9093`, `5601`

### 2. SSH into the server

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<ec2-public-ip>
```

### 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
newgrp docker
```

### 4. Clone and configure

```bash
git clone https://github.com/sparkling-snail/lta-proxy
cd lta-proxy
cp .env.example .env
nano .env   # paste your LTA_API_KEY
```

### 5. Start the stack

```bash
# Full stack with ELK (t3.medium):
docker compose up -d --build

# Without ELK (t3.micro):
docker compose -f docker-compose.prod.yml up -d --build
```

### 6. Open dashboards

Replace `<ec2-ip>` with your EC2 public IP:

- React UI: `http://<ec2-ip>:5173`
- Grafana: `http://<ec2-ip>:3000` (admin / admin)
- Prometheus: `http://<ec2-ip>:9090`
- Alertmanager: `http://<ec2-ip>:9093`
- Kibana: `http://<ec2-ip>:5601`

### 7. Useful server commands

```bash
docker compose logs -f app       # stream app logs
docker compose ps                # check container status
docker compose down              # stop everything
docker compose up -d             # start in background
```

---

## Key bus stop codes to try

| Stop code | Location |
| --------- | -------- |
| 83139 | Sengkang Bus Interchange |
| 75009 | Tampines Bus Interchange |
| 01012 | Victoria St opp. National Library |
| 65199 | Compassvale Rd |

## Runbooks

- [Fast burn alert](runbooks/fast-burn.md)
- [Slow burn alert](runbooks/slow-burn.md)
- [High latency alert](runbooks/high-latency.md)
- [Stale cache alert](runbooks/stale-cache.md)
