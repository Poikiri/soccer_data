"""
Pulls match and event data from the StatsBomb open-data repo and lands it
raw and unmodified in Postgres (one JSONB blob per match, one per event).
Idempotent: skips matches whose events are already loaded.
"""
import os

import psycopg2
import requests
from psycopg2.extras import Json, execute_values

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# (competition_id, season_id). Start with one full domestic season -- add
# more once this proves out. See data/competitions.json in the statsbomb/open-data
# repo for the full list of what's available.
COMPETITIONS = [
    (37, 4),  # FA Women's Super League, 2018/2019
]

CREATE_RAW_TABLES = """
create schema if not exists raw;

create table if not exists raw.sb_matches (
    match_id int primary key,
    competition_id int not null,
    season_id int not null,
    match_json jsonb not null,
    ingested_at timestamptz not null default now()
);

create table if not exists raw.sb_events (
    match_id int not null,
    event_id text not null,
    event_json jsonb not null,
    ingested_at timestamptz not null default now(),
    unique (match_id, event_id)
);
"""


def fetch_json(path: str):
    resp = requests.get(f"{BASE_URL}/{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "soccer"),
        password=os.environ.get("PGPASSWORD", "soccer"),
        dbname=os.environ.get("PGDATABASE", "soccer"),
        sslmode=os.environ.get("PGSSLMODE", "prefer"),
    )


def run() -> int:
    conn = get_connection()
    events_inserted = 0
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_RAW_TABLES)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("select distinct match_id from raw.sb_events")
            already_loaded = {row[0] for row in cur.fetchall()}

        for competition_id, season_id in COMPETITIONS:
            matches = fetch_json(f"matches/{competition_id}/{season_id}.json")
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    insert into raw.sb_matches (match_id, competition_id, season_id, match_json)
                    values %s
                    on conflict (match_id) do nothing
                    """,
                    [(m["match_id"], competition_id, season_id, Json(m)) for m in matches],
                )
            conn.commit()
            print(f"competition {competition_id} season {season_id}: {len(matches)} matches")

            new_matches = [m for m in matches if m["match_id"] not in already_loaded]
            for m in new_matches:
                match_id = m["match_id"]
                events = fetch_json(f"events/{match_id}.json")
                with conn.cursor() as cur:
                    inserted_ids = execute_values(
                        cur,
                        """
                        insert into raw.sb_events (match_id, event_id, event_json)
                        values %s
                        on conflict (match_id, event_id) do nothing
                        returning event_id
                        """,
                        [(match_id, e["id"], Json(e)) for e in events],
                        page_size=1000,
                        fetch=True,
                    )
                    events_inserted += len(inserted_ids)
                conn.commit()
            print(f"  fetched events for {len(new_matches)} new matches ({len(matches) - len(new_matches)} already loaded)")
    finally:
        conn.close()
    return events_inserted


if __name__ == "__main__":
    total = run()
    print(f"Done. {total} new events inserted.")
