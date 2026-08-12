with team_matches as (
    select
        home_team as team, 'home' as venue,
        home_goals as goals_for, away_goals as goals_against,
        case when result = 'H' then 3 when result = 'D' then 1 else 0 end as points,
        case when result = 'H' then 1 else 0 end as win,
        case when result = 'D' then 1 else 0 end as draw,
        case when result = 'A' then 1 else 0 end as loss
    from {{ ref('fct_matches') }}

    union all

    select
        away_team as team, 'away' as venue,
        away_goals as goals_for, home_goals as goals_against,
        case when result = 'A' then 3 when result = 'D' then 1 else 0 end as points,
        case when result = 'A' then 1 else 0 end as win,
        case when result = 'D' then 1 else 0 end as draw,
        case when result = 'H' then 1 else 0 end as loss
    from {{ ref('fct_matches') }}
)

select
    team,
    venue,
    count(*) as matches_played,
    sum(win) as wins,
    sum(draw) as draws,
    sum(loss) as losses,
    sum(goals_for) as goals_for,
    sum(goals_against) as goals_against,
    sum(points) as points,
    round(avg(points), 2) as avg_points_per_match
from team_matches
group by team, venue
order by team, venue
