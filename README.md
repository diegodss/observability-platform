# Observability platform

Monitoring, alerting and alert correlation for the
[observability-env-simulator](https://github.com/diegodss/observability-env-simulator). The simulator
plays "production": Technology One (SM), EDW and three AppEvents integrations. This repo watches it,
and it's where the alerting pipeline is built:

```
simulator services ──▶ Prometheus ──▶ alert rules ──▶ [Alertmanager / Keep] ──▶ Jira Assets lookup ──▶ Jira ticket
                          │                              (next)                  (model ready)          (templates ready)
                          └──▶ Grafana dashboard
```

| Piece | Status |
|---|---|
| Prometheus scraping the 5 simulator services, with `ci_name` labels | ✅ running |
| Alert rules (target/source down, integration failed, stale) | ✅ evaluated, shown at `/alerts` |
| Grafana dashboard (health, timeline, runs, failures, data) | ✅ provisioned |
| Jira Assets model (Integrations + Applications schemas, optional connectors) | ✅ CSVs, load script, offline validator, lookup test |
| Incident ticket templates (application, integration, connector) | ✅ designed |
| Alertmanager / Keep, Jira Assets enrichment, Jira ticket creation | ⏳ next |

> **Not production-hardened.** Local development setup: default Grafana credentials, anonymous
> viewing, ports bound to `127.0.0.1`.

## Setup

Clone both repos side by side:

```bash
git clone https://github.com/diegodss/observability-env-simulator.git
git clone https://github.com/diegodss/observability-platform.git
```

**1. Start the simulator first.** It creates the shared Docker network `observability-sim`:

```bash
cd observability-env-simulator
docker compose up --build -d
```

**2. Start the platform:**

```bash
cd ../observability-platform
docker compose up -d
```

If the platform says *network observability-sim declared as external, but could not be found*,
the simulator isn't running yet; do step 1 first.

| UI | URL |
|---|---|
| Grafana: home dashboard **Education Integration - Jobs and EDW health** (anonymous view; `admin` / `admin` to edit) | http://localhost:3000 |
| Prometheus targets (all 5 should be UP) | http://localhost:9090/targets |
| Prometheus alerts | http://localhost:9090/alerts |

**Stop** with `docker compose down`, or `down -v` to also drop Prometheus history. The two repos
start and stop independently. Stop the platform before running `down` in the simulator, because the
simulator owns the shared network and can't remove it while the platform is still attached.

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
compose.yaml                   Prometheus + Grafana, joined to the simulator's network
prometheus/prometheus.yml      scrape jobs, with ci_name / display_name labels
prometheus/rules.yml           alert rules
grafana/provisioning/          datasource and dashboard provider
grafana/dashboards/            the provisioned dashboard (JSON)
docs/alerting.md               scrape jobs and alert rules explained
docs/jira-assets/              Jira Assets model: schemas, initial-load scope, import CSVs
docs/incident-templates.md     Jira incident ticket templates
scripts/                       Jira Assets tools (initial load, offline validator, lookup test)
```

## How alerts map to the CMDB

Every scraped series carries `ci_name`, the exact name of the CI in Jira Assets:
- the applications are `Technology One (SM)` and `EDW`;
- the integrations are the full `ETL - DXMULTI-0001 : AppEvents from SMS to EDW …` names.

Keep (or any correlator) looks that name up and follows the CI's references:
- **Target System** gives the root CI;
- **Resolver Group** says who gets the ticket.

Details:
- [docs/alerting.md](docs/alerting.md): scrape jobs and alert rules;
- [docs/jira-assets/README.md](docs/jira-assets/README.md): the schemas, the one-off SOT initial load
  and the lookup test;
- [docs/incident-templates.md](docs/incident-templates.md): the ticket layouts.

### Jira Assets tools

```bash
python3 scripts/preview-assets-graph.py                                   # offline check of the import CSVs
python3 scripts/sot-initial-load.py "/path/to/Integrations SOT(Integrations).csv"  # regenerate them from the SOT (once)
python3 scripts/test-assets-lookup.py                                     # read-only check against Jira Assets
```

The lookup test needs `JIRA_SITE`, `JIRA_EMAIL` and `JIRA_API_TOKEN` (see `.env.example`). The SOT
file is internal and isn't in this repo.

## Configuration

Defaults are in `compose.yaml`; override them in `.env` (see `.env.example`):
- `PROMETHEUS_HOST_PORT` (9090) and `GRAFANA_HOST_PORT` (3000);
- `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`;
- the Jira variables used by the lookup test.

## Next steps

1. **Alertmanager or Keep** as the receiver for the Prometheus alerts.
2. **Enrichment:** look up each alert's `ci_name` in Jira Assets, using the same queries the lookup
   test runs.
3. **Correlation:** group alerts by root CI, with application → connector → integration precedence.
4. **Ticketing:** create and update the Jira incident from the templates, and auto-resolve it when the
   alerts clear.
