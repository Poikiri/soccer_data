# Soccer Data Pipeline

Scheduled ELT pipeline: pulls English Premier League results from
[football-data.co.uk](https://www.football-data.co.uk), lands them raw in
Postgres, then uses dbt to build a small modeled warehouse (team form,
home/away splits), with tests that fail the run on bad or stale data.

## Architecture

```
football-data.co.uk (CSV)
        |
        v
ingest/ingest_matches.py  --> raw.matches (Postgres, unmodified landing)
        |
        v
dbt: stg_matches (typed/cleaned)
        |
        +--> dim_teams
        +--> fct_matches (joins teams, real FKs)
                |
                +--> team_form (rolling 5-match points/goal diff)
                +--> home_away_splits (W/D/L, points, home vs away)

flows/pipeline.py (Prefect) wires it together:
  ingest -> dbt source freshness -> dbt run -> dbt test
```

Ingestion is idempotent: `raw.matches` has a unique constraint on
`(div, date, hometeam, awayteam)` and inserts use `ON CONFLICT DO NOTHING`, so
a rerun only adds fixtures that aren't already loaded.

Scope note: this covers football-data.co.uk only. The xG-differential mart
from the original spec needs StatsBomb event data, which isn't wired in yet.

## Run it

Requires Docker and Python 3.11+.

```bash
make bootstrap
```

This starts Postgres, installs dependencies into `.venv`, and runs the
pipeline once end-to-end (ingest -> freshness check -> dbt run -> dbt test).

To browse the warehouse:

```bash
docker compose exec postgres psql -U soccer -d soccer -c "select * from home_away_splits limit 10;"
```

## Run it on a schedule

```bash
make serve
```

Keeps a Prefect process alive that fires the same flow every Monday and
Thursday morning (the source updates Sunday/Wednesday nights). Leave it
running, or point Prefect's process manager / a `launchd`/`systemd` unit /
cron at `make run` instead if you'd rather not keep a long-lived process.

## Data quality tests

`dbt test` checks (see `dbt/soccer/models/**/*.yml`):

- `stg_matches`: primary key not-null/unique, required fields not-null,
  `result` restricted to `H`/`D`/`A`.
- `fct_matches`: primary key not-null/unique, `home_team_id`/`away_team_id`
  not-null **and** must exist in `dim_teams` (referential integrity).
- `dbt source freshness` on `raw.matches`: warns after 4 days without a new
  row, errors after 8 (the source updates twice a week).

To see a test fail on purpose:

```bash
docker compose exec postgres psql -U soccer -d soccer \
  -c "insert into raw.matches (div, date, hometeam, awayteam, ftr, source_season) values ('E0', '01/01/2099', 'Test FC', 'Nowhere FC', 'X', '9999');"
make run
```

The bogus `ftr = 'X'` value fails the `accepted_values` test on
`stg_matches.result`, and `dbt test` exits non-zero, so the flow run fails
instead of silently building marts on top of it.

## Project layout

- `ingest/ingest_matches.py` — pulls CSVs, lands raw rows in Postgres.
- `dbt/soccer/` — dbt project (staging + marts + tests + source freshness).
- `flows/pipeline.py` — Prefect flow tying ingest + dbt together, with the
  schedule.
- `docker-compose.yml` — local Postgres.
