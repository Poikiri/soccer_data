"""
Orchestrates the ELT run: ingest raw data, check source freshness, build dbt
models, then test them. Any step failing raises, so Prefect marks the run
failed instead of quietly producing bad marts.
"""
import os
import subprocess
import sys
from pathlib import Path

from prefect import flow, task

REPO_ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = REPO_ROOT / "dbt" / "soccer"
DBT_BIN = Path(sys.executable).parent / "dbt"


@task(retries=2, retry_delay_seconds=30)
def ingest():
    sys.path.insert(0, str(REPO_ROOT / "ingest"))
    import ingest_matches
    return ingest_matches.run()


@task(retries=2, retry_delay_seconds=30)
def ingest_statsbomb():
    sys.path.insert(0, str(REPO_ROOT / "ingest"))
    import ingest_statsbomb
    return ingest_statsbomb.run()


def _run_dbt(*args: str) -> None:
    result = subprocess.run(
        [str(DBT_BIN), *args, "--project-dir", str(DBT_PROJECT_DIR), "--profiles-dir", str(DBT_PROJECT_DIR)],
        capture_output=True, text=True,
    )
    print(result.stdout)
    print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"dbt {' '.join(args)} failed (exit {result.returncode})")


@task
def dbt_source_freshness():
    _run_dbt("source", "freshness")


@task
def dbt_run():
    _run_dbt("run")


@task
def dbt_test():
    _run_dbt("test")


# StatsBomb-derived models only -- rebuilding the football-data.co.uk models
# on every StatsBomb run would be harmless but pointless.
STATSBOMB_MODELS = ["stg_sb_matches", "stg_sb_events", "xg_form"]


@task
def dbt_run_statsbomb():
    _run_dbt("run", "--select", *STATSBOMB_MODELS)


@task
def dbt_test_statsbomb():
    _run_dbt("test", "--select", *STATSBOMB_MODELS)


@flow(name="soccer-elt")
def soccer_pipeline():
    ingest()
    dbt_source_freshness()
    dbt_run()
    dbt_test()


@flow(name="statsbomb-elt")
def statsbomb_pipeline():
    ingest_statsbomb()
    dbt_run_statsbomb()
    dbt_test_statsbomb()


if __name__ == "__main__":
    if os.environ.get("PREFECT_SERVE") == "1":
        # football-data.co.uk refreshes Sunday and Wednesday nights, so check
        # for new fixtures Monday and Thursday mornings.
        soccer_pipeline.serve(name="soccer-elt-scheduled", cron="0 6 * * mon,thu")
    else:
        soccer_pipeline()
