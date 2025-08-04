| table_name                   | column_name          | data_type                |
| ---------------------------- | -------------------- | ------------------------ |
| comparison_cache             | id                   | uuid                     |
| comparison_cache             | establishment_id     | uuid                     |
| comparison_cache             | comparison_type      | character varying        |
| comparison_cache             | dimension1           | character varying        |
| comparison_cache             | dimension2           | character varying        |
| comparison_cache             | metric               | character varying        |
| comparison_cache             | group1_mean          | numeric                  |
| comparison_cache             | group1_std_dev       | numeric                  |
| comparison_cache             | group1_count         | integer                  |
| comparison_cache             | group2_mean          | numeric                  |
| comparison_cache             | group2_std_dev       | numeric                  |
| comparison_cache             | group2_count         | integer                  |
| comparison_cache             | mean_difference      | numeric                  |
| comparison_cache             | percent_change       | numeric                  |
| comparison_cache             | cohen_d              | numeric                  |
| comparison_cache             | p_value              | numeric                  |
| comparison_cache             | ai_insights          | jsonb                    |
| comparison_cache             | created_at           | timestamp with time zone |
| comparison_cache             | expires_at           | timestamp with time zone |
| current_school_averages      | establishment_id     | uuid                     |
| current_school_averages      | establishment_name   | character varying        |
| current_school_averages      | cycle                | integer                  |
| current_school_averages      | element              | character varying        |
| current_school_averages      | mean                 | numeric                  |
| current_school_averages      | std_dev              | numeric                  |
| current_school_averages      | count                | integer                  |
| current_school_averages      | academic_year        | character varying        |
| dashboard_user_access        | user_email           | character varying        |
| dashboard_user_access        | establishment_id     | uuid                     |
| dashboard_user_access        | establishment_name   | character varying        |
| dashboard_user_access        | user_role            | text                     |
| dashboard_user_access        | staff_admin_knack_id | character varying        |
| dashboard_user_access        | super_user_knack_id  | character varying        |
| establishments               | id                   | uuid                     |
| establishments               | knack_id             | character varying        |
| establishments               | name                 | character varying        |
| establishments               | trust_id             | uuid                     |
| establishments               | is_australian        | boolean                  |
| establishments               | created_at           | timestamp with time zone |
| establishments               | updated_at           | timestamp with time zone |
| establishments               | status               | character varying        |
| national_question_statistics | id                   | uuid                     |
| national_question_statistics | question_id          | character varying        |
| national_question_statistics | cycle                | integer                  |
| national_question_statistics | academic_year        | character varying        |
| national_question_statistics | mean                 | numeric                  |
| national_question_statistics | std_dev              | numeric                  |
| national_question_statistics | count                | integer                  |
| national_question_statistics | mode                 | integer                  |
| national_question_statistics | percentile_25        | numeric                  |
| national_question_statistics | percentile_75        | numeric                  |
| national_question_statistics | distribution         | jsonb                    |
| national_question_statistics | calculated_at        | timestamp with time zone |
| national_statistics          | id                   | uuid                     |
| national_statistics          | cycle                | integer                  |
| national_statistics          | academic_year        | character varying        |
| national_statistics          | element              | character varying        |
| national_statistics          | mean                 | numeric                  |
| national_statistics          | std_dev              | numeric                  |
| national_statistics          | count                | integer                  |
| national_statistics          | percentile_25        | numeric                  |
| national_statistics          | percentile_50        | numeric                  |
| national_statistics          | percentile_75        | numeric                  |
| national_statistics          | distribution         | jsonb                    |
| national_statistics          | calculated_at        | timestamp with time zone |
| qla_question_performance     | id                   | uuid                     |
| qla_question_performance     | establishment_id     | uuid                     |
| qla_question_performance     | cycle                | integer                  |
| qla_question_performance     | academic_year        | character varying        |
| qla_question_performance     | question_id          | character varying        |
| qla_question_performance     | mean                 | numeric                  |
| qla_question_performance     | std_dev              | numeric                  |
| qla_question_performance     | count                | integer                  |
| qla_question_performance     | distribution         | jsonb                    |
| qla_question_performance     | calculated_at        | timestamp with time zone |
| qla_question_performance     | mode                 | integer                  |
| qla_question_performance     | percentile_25        | numeric                  |
| qla_question_performance     | percentile_75        | numeric                  |
| qla_question_performance     | rank_high_to_low     | bigint                   |
| qla_question_performance     | rank_low_to_high     | bigint                   |
| qla_question_performance     | national_mean        | numeric                  |
| qla_question_performance     | national_std_dev     | numeric                  |
| qla_question_performance     | national_count       | integer                  |
| qla_question_performance     | diff_from_national   | numeric                  |
| qla_question_performance     | performance_category | text                     |
| qla_question_performance     | national_comparison  | text                     |
| question_rankings            | id                   | uuid                     |
| question_rankings            | establishment_id     | uuid                     |
| question_rankings            | cycle                | integer                  |
| question_rankings            | academic_year        | character varying        |
| question_rankings            | question_id          | character varying        |
| question_rankings            | mean                 | numeric                  |
| question_rankings            | std_dev              | numeric                  |
| question_rankings            | count                | integer                  |
| question_rankings            | distribution         | jsonb                    |
| question_rankings            | calculated_at        | timestamp with time zone |
| question_rankings            | mode                 | integer                  |
| question_rankings            | percentile_25        | numeric                  |
| question_rankings            | percentile_75        | numeric                  |
| question_rankings            | rank_desc            | bigint                   |