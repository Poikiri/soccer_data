"""
Pulls match CSVs from football-data.co.uk and lands them raw and unmodified
in Postgres. Idempotent: re-running only inserts fixtures not already loaded.
"""
import csv
import io
import os

import psycopg2
import requests

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{div}.csv"

# One division (Premier League), a few seasons for history.
DIVISIONS = ["E0"]
SEASONS = ["2223", "2324", "2425", "2526"]

# Core match columns we keep. football-data.co.uk also ships ~100 betting-odds
# columns per row; those aren't needed by anything downstream, so we don't land them.
RAW_COLUMNS = [
    "Div", "Date", "Time", "HomeTeam", "AwayTeam",
    "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
    "Referee", "HS", "AS", "HST", "AST", "HF", "AF",
    "HC", "AC", "HY", "AY", "HR", "AR",
]

CREATE_RAW_TABLE = """
create schema if not exists raw;

create table if not exists raw.matches (
    div text, date text, time text, hometeam text, awayteam text,
    fthg text, ftag text, ftr text, hthg text, htag text, htr text,
    referee text, hs text, "as" text, hst text, ast text, hf text, af text,
    hc text, ac text, hy text, ay text, hr text, ar text,
    source_season text not null,
    ingested_at timestamptz not null default now(),
    unique (div, date, hometeam, awayteam)
);
"""

INSERT_ROW = """
insert into raw.matches (
    div, date, time, hometeam, awayteam,
    fthg, ftag, ftr, hthg, htag, htr,
    referee, hs, "as", hst, ast, hf, af,
    hc, ac, hy, ay, hr, ar, source_season
) values (
    %(Div)s, %(Date)s, %(Time)s, %(HomeTeam)s, %(AwayTeam)s,
    %(FTHG)s, %(FTAG)s, %(FTR)s, %(HTHG)s, %(HTAG)s, %(HTR)s,
    %(Referee)s, %(HS)s, %(AS)s, %(HST)s, %(AST)s, %(HF)s, %(AF)s,
    %(HC)s, %(AC)s, %(HY)s, %(AY)s, %(HR)s, %(AR)s, %(source_season)s
)
on conflict (div, date, hometeam, awayteam) do nothing;
"""


def fetch_season_csv(div: str, season: str) -> list[dict]:
    url = BASE_URL.format(season=season, div=div)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.content.decode("utf-8-sig")))
    rows = []
    for row in reader:
        if not row.get("Div"):
            continue
        rows.append({col: row.get(col, "") for col in RAW_COLUMNS})
    return rows


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "soccer"),
        password=os.environ.get("PGPASSWORD", "soccer"),
        dbname=os.environ.get("PGDATABASE", "soccer"),
    )


def run() -> int:
    conn = get_connection()
    inserted = 0
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_RAW_TABLE)
        conn.commit()

        for div in DIVISIONS:
            for season in SEASONS:
                rows = fetch_season_csv(div, season)
                with conn.cursor() as cur:
                    for row in rows:
                        row["source_season"] = season
                        cur.execute(INSERT_ROW, row)
                        inserted += cur.rowcount
                conn.commit()
                print(f"{div} {season}: fetched {len(rows)} rows, inserted {inserted} so far")
    finally:
        conn.close()
    return inserted


if __name__ == "__main__":
    total = run()
    print(f"Done. {total} new rows inserted.")
