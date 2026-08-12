with teams as (
    select home_team as team_name from {{ ref('stg_matches') }}
    union
    select away_team as team_name from {{ ref('stg_matches') }}
)

select
    md5(team_name) as team_id,
    team_name
from teams
