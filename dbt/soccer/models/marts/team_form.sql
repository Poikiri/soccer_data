with team_matches as (
    select
        match_id, match_date,
        home_team as team, away_team as opponent,
        home_goals as goals_for, away_goals as goals_against,
        case when result = 'H' then 3 when result = 'D' then 1 else 0 end as points
    from {{ ref('fct_matches') }}

    union all

    select
        match_id, match_date,
        away_team as team, home_team as opponent,
        away_goals as goals_for, home_goals as goals_against,
        case when result = 'A' then 3 when result = 'D' then 1 else 0 end as points
    from {{ ref('fct_matches') }}
)

select
    *,
    goals_for - goals_against as goal_diff,
    sum(points) over (
        partition by team order by match_date
        rows between 4 preceding and current row
    ) as points_last_5,
    sum(goals_for - goals_against) over (
        partition by team order by match_date
        rows between 4 preceding and current row
    ) as goal_diff_last_5
from team_matches
order by team, match_date
