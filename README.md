# Observability platform

Monitoring, alerting and alert correlation for the
[observability-env-simulator](https://github.com/diegodss/observability-env-simulator). The simulator
plays "production": Technology One (SM), EDW and three AppEvents integrations. This repo watches it,
and it's where the alerting pipeline is built:

```
simulator services ──▶ Prometheus ──▶ alert rules ──▶ [Alertmanager / Keep] ──▶ CMDB API ──▶ Jira ticket
                          │                              (next)                  (observability-cmdb)  (templates ready)
                          └──▶ Grafana dashboard
```

| Piece | Status |
|---|---|
| Prometheus scraping the 5 simulator services, with `ci_name` labels | ✅ running |
| Alert rules (target/source down, integration failed, stale) | ✅ evaluated, shown at `/alerts` |
| Grafana dashboard (health, timeline, runs, failures, data) | ✅ provisioned |
| Jira Assets schemas and CMDB API | ✅ in [observability-cmdb](https://github.com/diegodss/observability-cmdb) (`GET /ci/{ci_name}`) |
| Incident ticket templates (application, integration, connector) | ✅ designed |
| Alertmanager / Keep calling the CMDB API, Jira ticket creation | ⏳ next |

> **Not production-hardened.** Local development setup: default Grafana credentials, anonymous
> viewing, ports bound to `127.0.0.1`.

## Setup

Clone both repos side by side:

```bash
git clone https://github.com/diegodss/observability-env-simulator.git
git clone https://github.com/diegodss/observability-platform.git
```

Start both, in either order:

```bash
cd observability-env-simulator && docker compose up --build -d
cd ../observability-platform && docker compose up -d
```

Both repos declare the same Docker network, `observability-sim`, which is how Prometheus reaches
the simulator's services by name. Whichever stack starts second logs a harmless warning that the
network "was not created for project …"; that's expected. Until the simulator is up, its targets
show as DOWN.

| UI | URL |
|---|---|
| Grafana: home dashboard **Education Integration - Jobs and EDW health** (anonymous view; `admin` / `admin` to edit) | http://localhost:3000 |
| Prometheus targets (all 5 should be UP) | http://localhost:9090/targets |
| Prometheus alerts | http://localhost:9090/alerts |

**Stop** with `docker compose down`, or `down -v` to also drop Prometheus history. The two repos
start and stop independently, in any order. The shared network is removed when the last stack using
it goes down.

## See it work

In the **simulator** folder:

```bash
docker compose stop edw
```

Within about a minute, on the platform:
- **Grafana:** EDW turns DOWN and the three flows turn FAILED; on the timeline, the flows go red right
  after EDW.
- **Prometheus `/alerts`:** `TargetSystemUnavailable` (EDW) plus three `IntegrationLastRunFailed`
  fire. They're pending for 20 s, then firing.

Then recover:

```bash
docker compose start edw
```

Everything turns green and the alerts clear. More scenarios (source outage, single worker down, data
update) are in the simulator's README.

## Repository layout

```
compose.yaml                   Prometheus + Grafana, on the network shared with the simulator
prometheus/prometheus.yml      scrape jobs, with ci_name / display_name labels
prometheus/rules.yml           alert rules
grafana/provisioning/          datasource and dashboard provider
grafana/dashboards/            the provisioned dashboard (JSON)
docs/alerting.md               scrape jobs and alert rules explained
docs/incident-templates.md     Jira incident ticket templates
```

## How alerts map to the CMDB

Every scraped series carries `ci_name`, the exact name of the CI in Jira Assets:
- the applications are `Technology One (SM)` and `EDW`;
- the integrations are the full `ETL - DXMULTI-0001 : AppEvents from SMS to EDW …` names.

The CMDB side lives in [observability-cmdb](https://github.com/diegodss/observability-cmdb): the three Jira Assets schemas as code
(plan/apply), and the CMDB API on the shared network. Keep calls it with the alert's label:

```
GET http://cmdb:8080/ci/{ci_name}?failed_side=target
Authorization: Bearer <CMDB_API_KEY>
```

The API requires the key set in the cmdb service's `CMDB_API_KEY`. Store it in Keep as a secret.

It returns the root CI, its **Resolver Group**, the informed groups, the impact (affected
integrations and domains) and **`routing`**, the Jira project and labels for the ticket.

**Tickets are ordinary Jira issues** (no Jira Service Management). For now every incident goes to
one project, labelled per resolver group (e.g. `resolver-data-squad`). When squads get their own
projects, observability-cmdb's `data/routing.yaml` switches them over with no change here: Keep
always creates the issue in `routing.project` with `routing.labels`. See:
- [docs/alerting.md](docs/alerting.md): scrape jobs and alert rules;
- [docs/incident-templates.md](docs/incident-templates.md): the ticket layouts, filled from that response.

## Configuration

Defaults are in `compose.yaml`; override them in `.env` (see `.env.example`):
- `PROMETHEUS_HOST_PORT` (9090) and `GRAFANA_HOST_PORT` (3000);
- `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`.

## Next steps

1. **Alertmanager or Keep** as the receiver for the Prometheus alerts.
2. **Enrichment:** call the observability-cmdb API with each alert's `ci_name`.
3. **Correlation:** group alerts by root CI, with application → connector → integration precedence.
4. **Ticketing:** create and update the Jira incident from the templates, and auto-resolve it when the
   alerts clear.
