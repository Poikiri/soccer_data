with source as (
    select * from {{ source('raw', 'sb_events') }}
),

-- Shot events only -- the only event type this project uses so far
-- (it's what feeds statsbomb_xg into the xg_form mart).
shots as (
    select
        match_id,
        event_id,
        (event_json->>'minute')::int as minute,
        (event_json->'team'->>'id')::int as team_id,
        event_json->'team'->>'name' as team,
        event_json->'player'->>'name' as player,
        (event_json->'shot'->>'statsbomb_xg')::numeric as statsbomb_xg,
        event_json->'shot'->'outcome'->>'name' as outcome
    from source
    where event_json->'type'->>'name' = 'Shot'
)

select * from shots
