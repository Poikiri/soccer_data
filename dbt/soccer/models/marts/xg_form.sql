with match_shot_xg as (
    select
        match_id,
        team_id,
        sum(statsbomb_xg) as team_xg
    from {{ ref('stg_sb_events') }}
    group by match_id, team_id
),

team_matches as (
    select
        m.match_id, m.match_date,
        m.home_team_id as team_id, m.home_team as team, m.away_team as opponent,
        m.home_score as goals_for, m.away_score as goals_against,
        coalesce(hx.team_xg, 0) as xg_for,
        coalesce(ax.team_xg, 0) as xg_against
    from {{ ref('stg_sb_matches') }} m
    left join match_shot_xg hx on hx.match_id = m.match_id and hx.team_id = m.home_team_id
    left join match_shot_xg ax on ax.match_id = m.match_id and ax.team_id = m.away_team_id

    union all

    select
        m.match_id, m.match_date,
        m.away_team_id as team_id, m.away_team as team, m.home_team as opponent,
        m.away_score as goals_for, m.home_score as goals_against,
        coalesce(ax.team_xg, 0) as xg_for,
        coalesce(hx.team_xg, 0) as xg_against
    from {{ ref('stg_sb_matches') }} m
    left join match_shot_xg hx on hx.match_id = m.match_id and hx.team_id = m.home_team_id
    left join match_shot_xg ax on ax.match_id = m.match_id and ax.team_id = m.away_team_id
)

select
    *,
    goals_for - goals_against as goal_diff,
    round(xg_for - xg_against, 2) as xg_diff,
    round(sum(xg_for) over (
        partition by team order by match_date
        rows between 4 preceding and current row
    ), 2) as xg_for_last_5,
    round(sum(xg_against) over (
        partition by team order by match_date
        rows between 4 preceding and current row
    ), 2) as xg_against_last_5,
    sum(goals_for) over (
        partition by team order by match_date
        rows between 4 preceding and current row
    ) as goals_for_last_5
from team_matches
order by team, match_date
