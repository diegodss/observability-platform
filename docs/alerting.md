# Scraping and alert rules

## Scrape jobs

`prometheus/prometheus.yml` scrapes the five services of the
[observability-env-simulator](https://github.com/diegodss/observability-env-simulator) every 10 s,
over the shared Docker network `observability-sim`.

| Job | Target | `ci_name` (Jira Assets CI) | `display_name` |
|---|---|---|---|
| `technology-one-sm` | `technology-one-sm:8000` | Technology One (SM) | Technology One (SM) |
| `edw` | `edw:8000` | EDW | EDW |
| `appevents-student` | `appevents-student:9100` | ETL - DXMULTI-0001 : AppEvents from SMS to EDW - Student | AppEvents - Student |
| `appevents-curriculum` | `appevents-curriculum:9100` | ETL - DXMULTI-0001 : AppEvents from SMS to EDW - Curriculum | AppEvents - Curriculum |
| `appevents-general` | `appevents-general:9100` | ETL - DXMULTI-0001 : AppEvents from SMS to EDW | AppEvents - General |

Labels attached to every series:
- `ci_name`: the exact Jira Assets object name; it's how alerts are matched to CIs;
- `display_name`: a short label for dashboards.

The metric catalogue itself (names, labels, error types) is the simulator's telemetry contract:
[docs/metrics.md](https://github.com/diegodss/observability-env-simulator/blob/main/docs/metrics.md)
in that repo.

## Alert rules

Defined in `prometheus/rules.yml` and shown at http://localhost:9090/alerts. No Alertmanager is
configured yet, so nothing is sent anywhere.

| Alert | Expression | `for` | Meaning |
|---|---|---|---|
| `TargetSystemUnavailable` | `up{job="edw"} == 0` | 20s | EDW cannot be scraped (Prometheus `up`, not `app_up`) |
| `SourceSystemUnavailable` | `up{job="technology-one-sm"} == 0` | 20s | Technology One (SM) cannot be scraped |
| `AppUnhealthy` | `app_up{app=~"technology-one-sm\|edw"} == 0` | 20s | process up but its database is not |
| `IntegrationLastRunFailed` | `integration_last_run_success == 0 and on(integration) integration_runs_total{outcome="failure"} > 0` | – | latest run failed, after at least one completed run (label `dependency="edw"`) |
| `IntegrationStale` | `time() - integration_last_success_timestamp_seconds > 90` | – | no successful run for over 90 s |

During an EDW outage (`docker compose stop edw` in the simulator), `TargetSystemUnavailable` fires
together with three `IntegrationLastRunFailed`. A correlator groups them in two steps:
1. look up each alert's `ci_name` in Jira Assets;
2. follow each integration's **Target System** to EDW, the shared root CI.

The lookup is done by the enrichment service in [observability-cmdb](https://github.com/diegodss/observability-cmdb) (`GET http://enricher:8080/ci/{ci_name}`). The ticket layouts are in [incident-templates.md](incident-templates.md).
