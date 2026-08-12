select
    m.match_id,
    m.division,
    m.match_date,
    m.source_season,
    ht.team_id as home_team_id,
    awt.team_id as away_team_id,
    m.home_team,
    m.away_team,
    m.home_goals,
    m.away_goals,
    m.result,
    m.home_shots,
    m.away_shots,
    m.home_shots_on_target,
    m.away_shots_on_target,
    m.home_corners,
    m.away_corners
from {{ ref('stg_matches') }} m
left join {{ ref('dim_teams') }} ht on m.home_team = ht.team_name
left join {{ ref('dim_teams') }} awt on m.away_team = awt.team_name
