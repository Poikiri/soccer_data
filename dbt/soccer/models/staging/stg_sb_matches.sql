with source as (
    select * from {{ source('raw', 'sb_matches') }}
),

cleaned as (
    select
        match_id,
        competition_id,
        season_id,
        (match_json->>'match_date')::date as match_date,
        (match_json->'home_team'->>'home_team_id')::int as home_team_id,
        match_json->'home_team'->>'home_team_name' as home_team,
        (match_json->'away_team'->>'away_team_id')::int as away_team_id,
        match_json->'away_team'->>'away_team_name' as away_team,
        (match_json->>'home_score')::int as home_score,
        (match_json->>'away_score')::int as away_score
    from source
)

select * from cleaned
