with source as (
    select * from {{ source('raw', 'matches') }}
),

cleaned as (
    select
        md5(div || date || hometeam || awayteam) as match_id,
        div as division,
        to_date(date, 'DD/MM/YYYY') as match_date,
        hometeam as home_team,
        awayteam as away_team,
        nullif(fthg, '')::int as home_goals,
        nullif(ftag, '')::int as away_goals,
        ftr as result,
        nullif(hthg, '')::int as home_goals_ht,
        nullif(htag, '')::int as away_goals_ht,
        htr as result_ht,
        nullif(referee, '') as referee,
        nullif(hs, '')::int as home_shots,
        nullif("as", '')::int as away_shots,
        nullif(hst, '')::int as home_shots_on_target,
        nullif(ast, '')::int as away_shots_on_target,
        nullif(hc, '')::int as home_corners,
        nullif(ac, '')::int as away_corners,
        nullif(hy, '')::int as home_yellow_cards,
        nullif(ay, '')::int as away_yellow_cards,
        nullif(hr, '')::int as home_red_cards,
        nullif(ar, '')::int as away_red_cards,
        source_season
    from source
)

select * from cleaned
