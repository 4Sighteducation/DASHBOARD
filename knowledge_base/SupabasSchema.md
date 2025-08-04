| table_name                   | column_name                 | data_type                |
| ---------------------------- | --------------------------- | ------------------------ |
| comparison_cache             | id                          | uuid                     |
| comparison_cache             | establishment_id            | uuid                     |
| comparison_cache             | comparison_type             | character varying        |
| comparison_cache             | dimension1                  | character varying        |
| comparison_cache             | dimension2                  | character varying        |
| comparison_cache             | metric                      | character varying        |
| comparison_cache             | group1_mean                 | numeric                  |
| comparison_cache             | group1_std_dev              | numeric                  |
| comparison_cache             | group1_count                | integer                  |
| comparison_cache             | group2_mean                 | numeric                  |
| comparison_cache             | group2_std_dev              | numeric                  |
| comparison_cache             | group2_count                | integer                  |
| comparison_cache             | mean_difference             | numeric                  |
| comparison_cache             | percent_change              | numeric                  |
| comparison_cache             | cohen_d                     | numeric                  |
| comparison_cache             | p_value                     | numeric                  |
| comparison_cache             | ai_insights                 | jsonb                    |
| comparison_cache             | created_at                  | timestamp with time zone |
| comparison_cache             | expires_at                  | timestamp with time zone |
| current_school_averages      | establishment_id            | uuid                     |
| current_school_averages      | establishment_name          | character varying        |
| current_school_averages      | cycle                       | integer                  |
| current_school_averages      | element                     | character varying        |
| current_school_averages      | mean                        | numeric                  |
| current_school_averages      | std_dev                     | numeric                  |
| current_school_averages      | count                       | integer                  |
| current_school_averages      | academic_year               | character varying        |
| dashboard_user_access        | user_email                  | character varying        |
| dashboard_user_access        | establishment_id            | uuid                     |
| dashboard_user_access        | establishment_name          | character varying        |
| dashboard_user_access        | user_role                   | text                     |
| dashboard_user_access        | staff_admin_knack_id        | character varying        |
| dashboard_user_access        | super_user_knack_id         | character varying        |
| establishments               | id                          | uuid                     |
| establishments               | knack_id                    | character varying        |
| establishments               | name                        | character varying        |
| establishments               | trust_id                    | uuid                     |
| establishments               | is_australian               | boolean                  |
| establishments               | created_at                  | timestamp with time zone |
| establishments               | updated_at                  | timestamp with time zone |
| establishments               | status                      | character varying        |
| national_question_statistics | id                          | uuid                     |
| national_question_statistics | question_id                 | character varying        |
| national_question_statistics | cycle                       | integer                  |
| national_question_statistics | academic_year               | character varying        |
| national_question_statistics | mean                        | numeric                  |
| national_question_statistics | std_dev                     | numeric                  |
| national_question_statistics | count                       | integer                  |
| national_question_statistics | mode                        | integer                  |
| national_question_statistics | percentile_25               | numeric                  |
| national_question_statistics | percentile_75               | numeric                  |
| national_question_statistics | distribution                | jsonb                    |
| national_question_statistics | calculated_at               | timestamp with time zone |
| national_statistics          | id                          | uuid                     |
| national_statistics          | cycle                       | integer                  |
| national_statistics          | academic_year               | character varying        |
| national_statistics          | element                     | character varying        |
| national_statistics          | mean                        | numeric                  |
| national_statistics          | std_dev                     | numeric                  |
| national_statistics          | count                       | integer                  |
| national_statistics          | percentile_25               | numeric                  |
| national_statistics          | percentile_50               | numeric                  |
| national_statistics          | percentile_75               | numeric                  |
| national_statistics          | distribution                | jsonb                    |
| national_statistics          | calculated_at               | timestamp with time zone |
| qla_question_performance     | id                          | uuid                     |
| qla_question_performance     | establishment_id            | uuid                     |
| qla_question_performance     | cycle                       | integer                  |
| qla_question_performance     | academic_year               | character varying        |
| qla_question_performance     | question_id                 | character varying        |
| qla_question_performance     | mean                        | numeric                  |
| qla_question_performance     | std_dev                     | numeric                  |
| qla_question_performance     | count                       | integer                  |
| qla_question_performance     | distribution                | jsonb                    |
| qla_question_performance     | calculated_at               | timestamp with time zone |
| qla_question_performance     | mode                        | integer                  |
| qla_question_performance     | percentile_25               | numeric                  |
| qla_question_performance     | percentile_75               | numeric                  |
| qla_question_performance     | rank_high_to_low            | bigint                   |
| qla_question_performance     | rank_low_to_high            | bigint                   |
| qla_question_performance     | national_mean               | numeric                  |
| qla_question_performance     | national_std_dev            | numeric                  |
| qla_question_performance     | national_count              | integer                  |
| qla_question_performance     | diff_from_national          | numeric                  |
| qla_question_performance     | performance_category        | text                     |
| qla_question_performance     | national_comparison         | text                     |
| question_rankings            | id                          | uuid                     |
| question_rankings            | establishment_id            | uuid                     |
| question_rankings            | cycle                       | integer                  |
| question_rankings            | academic_year               | character varying        |
| question_rankings            | question_id                 | character varying        |
| question_rankings            | mean                        | numeric                  |
| question_rankings            | std_dev                     | numeric                  |
| question_rankings            | count                       | integer                  |
| question_rankings            | distribution                | jsonb                    |
| question_rankings            | calculated_at               | timestamp with time zone |
| question_rankings            | mode                        | integer                  |
| question_rankings            | percentile_25               | numeric                  |
| question_rankings            | percentile_75               | numeric                  |
| question_rankings            | rank_desc                   | bigint                   |
| question_rankings            | rank_asc                    | bigint                   |
| question_rankings            | total_questions             | bigint                   |
| question_rankings            | performance_category        | text                     |
| question_responses           | id                          | uuid                     |
| question_responses           | student_id                  | uuid                     |
| question_responses           | cycle                       | integer                  |
| question_responses           | question_id                 | character varying        |
| question_responses           | response_value              | integer                  |
| question_responses           | created_at                  | timestamp with time zone |
| question_statistics          | id                          | uuid                     |
| question_statistics          | establishment_id            | uuid                     |
| question_statistics          | cycle                       | integer                  |
| question_statistics          | academic_year               | character varying        |
| question_statistics          | question_id                 | character varying        |
| question_statistics          | mean                        | numeric                  |
| question_statistics          | std_dev                     | numeric                  |
| question_statistics          | count                       | integer                  |
| question_statistics          | distribution                | jsonb                    |
| question_statistics          | calculated_at               | timestamp with time zone |
| question_statistics          | mode                        | integer                  |
| question_statistics          | percentile_25               | numeric                  |
| question_statistics          | percentile_75               | numeric                  |
| questions                    | id                          | uuid                     |
| questions                    | question_id                 | character varying        |
| questions                    | question_text               | text                     |
| questions                    | vespa_category              | character varying        |
| questions                    | question_order              | integer                  |
| questions                    | current_cycle_field_id      | character varying        |
| questions                    | historical_cycle_field_base | character varying        |
| questions                    | field_id_cycle_1            | character varying        |
| questions                    | field_id_cycle_2            | character varying        |
| questions                    | field_id_cycle_3            | character varying        |
| questions                    | is_active                   | boolean                  |
| questions                    | created_at                  | timestamp with time zone |
| questions                    | updated_at                  | timestamp with time zone |
| report_templates             | id                          | uuid                     |
| report_templates             | name                        | character varying        |
| report_templates             | description                 | text                     |
| report_templates             | template_type               | character varying        |
| report_templates             | filters                     | jsonb                    |
| report_templates             | metrics                     | jsonb                    |
| report_templates             | visualizations              | jsonb                    |
| report_templates             | ai_prompt_template          | text                     |
| report_templates             | created_by                  | character varying        |
| report_templates             | created_at                  | timestamp with time zone |
| report_templates             | updated_at                  | timestamp with time zone |
| school_statistics            | id                          | uuid                     |
| school_statistics            | establishment_id            | uuid                     |
| school_statistics            | cycle                       | integer                  |
| school_statistics            | academic_year               | character varying        |
| school_statistics            | element                     | character varying        |
| school_statistics            | mean                        | numeric                  |
| school_statistics            | std_dev                     | numeric                  |
| school_statistics            | count                       | integer                  |
| school_statistics            | percentile_25               | numeric                  |
| school_statistics            | percentile_50               | numeric                  |
| school_statistics            | percentile_75               | numeric                  |
| school_statistics            | distribution                | jsonb                    |
| school_statistics            | calculated_at               | timestamp with time zone |
| school_statistics            | average                     | numeric                  |
| staff_admins                 | id                          | uuid                     |
| staff_admins                 | knack_id                    | character varying        |
| staff_admins                 | email                       | character varying        |
| staff_admins                 | name                        | character varying        |
| staff_admins                 | created_at                  | timestamp with time zone |
| staff_admins                 | updated_at                  | timestamp with time zone |
| staff_admins                 | establishment_id            | uuid                     |
| student_comments             | id                          | uuid                     |
| student_comments             | student_id                  | uuid                     |
| student_comments             | cycle                       | integer                  |
| student_comments             | comment_type                | character varying        |
| student_comments             | comment_text                | text                     |
| student_comments             | knack_field_id              | character varying        |
| student_comments             | created_at                  | timestamp with time zone |
| student_comments             | updated_at                  | timestamp with time zone |
| student_comments_aggregated  | establishment_id            | uuid                     |
| student_comments_aggregated  | year_group                  | character varying        |
| student_comments_aggregated  | course                      | character varying        |
| student_comments_aggregated  | faculty                     | character varying        |
| student_comments_aggregated  | group                       | character varying        |
| student_comments_aggregated  | cycle                       | integer                  |
| student_comments_aggregated  | comment_type                | character varying        |
| student_comments_aggregated  | comment_text                | text                     |
| student_comments_aggregated  | academic_year               | character varying        |
| student_vespa_progress       | student_id                  | uuid                     |
| student_vespa_progress       | student_name                | character varying        |
| student_vespa_progress       | email                       | character varying        |
| student_vespa_progress       | establishment_id            | uuid                     |
| student_vespa_progress       | establishment_name          | character varying        |
| student_vespa_progress       | year_group                  | character varying        |
| student_vespa_progress       | course                      | character varying        |
| student_vespa_progress       | faculty                     | character varying        |
| student_vespa_progress       | cycle1_vision               | integer                  |
| student_vespa_progress       | cycle1_effort               | integer                  |
| student_vespa_progress       | cycle1_systems              | integer                  |
| student_vespa_progress       | cycle1_practice             | integer                  |
| student_vespa_progress       | cycle1_attitude             | integer                  |
| student_vespa_progress       | cycle1_overall              | integer                  |
| student_vespa_progress       | cycle1_date                 | date                     |
| student_vespa_progress       | cycle2_vision               | integer                  |
| student_vespa_progress       | cycle2_effort               | integer                  |
| student_vespa_progress       | cycle2_systems              | integer                  |
| student_vespa_progress       | cycle2_practice             | integer                  |
| student_vespa_progress       | cycle2_attitude             | integer                  |
| student_vespa_progress       | cycle2_overall              | integer                  |
| student_vespa_progress       | cycle2_date                 | date                     |
| student_vespa_progress       | cycle3_vision               | integer                  |
| student_vespa_progress       | cycle3_effort               | integer                  |
| student_vespa_progress       | cycle3_systems              | integer                  |
| student_vespa_progress       | cycle3_practice             | integer                  |
| student_vespa_progress       | cycle3_attitude             | integer                  |
| student_vespa_progress       | cycle3_overall              | integer                  |
| student_vespa_progress       | cycle3_date                 | date                     |
| students                     | id                          | uuid                     |
| students                     | knack_id                    | character varying        |
| students                     | email                       | character varying        |
| students                     | name                        | character varying        |
| students                     | establishment_id            | uuid                     |
| students                     | year_group                  | character varying        |
| students                     | course                      | character varying        |
| students                     | faculty                     | character varying        |
| students                     | created_at                  | timestamp with time zone |
| students                     | updated_at                  | timestamp with time zone |
| students                     | group                       | character varying        |
| students                     | status                      | character varying        |
| super_users                  | id                          | uuid                     |
| super_users                  | knack_id                    | character varying        |
| super_users                  | email                       | character varying        |
| super_users                  | name                        | character varying        |
| super_users                  | created_at                  | timestamp with time zone |
| super_users                  | updated_at                  | timestamp with time zone |
| sync_logs                    | id                          | uuid                     |
| sync_logs                    | sync_type                   | character varying        |
| sync_logs                    | status                      | character varying        |
| sync_logs                    | records_processed           | integer                  |
| sync_logs                    | error_message               | text                     |
| sync_logs                    | started_at                  | timestamp with time zone |
| sync_logs                    | completed_at                | timestamp with time zone |
| sync_logs                    | metadata                    | jsonb                    |
| trusts                       | id                          | uuid                     |
| trusts                       | knack_id                    | character varying        |
| trusts                       | name                        | character varying        |
| trusts                       | created_at                  | timestamp with time zone |
| trusts                       | updated_at                  | timestamp with time zone |
| vespa_questions              | id                          | uuid                     |
| vespa_questions              | question_id                 | character varying        |
| vespa_questions              | question_text               | text                     |
| vespa_questions              | vespa_category              | character varying        |
| vespa_questions              | question_order              | integer                  |
| vespa_questions              | current_cycle_field_id      | character varying        |
| vespa_questions              | historical_cycle_field_base | character varying        |
| vespa_questions              | field_id_cycle_1            | character varying        |
| vespa_questions              | field_id_cycle_2            | character varying        |
| vespa_questions              | field_id_cycle_3            | character varying        |
| vespa_questions              | is_active                   | boolean                  |
| vespa_questions              | created_at                  | timestamp with time zone |
| vespa_questions              | updated_at                  | timestamp with time zone |
| vespa_scores                 | id                          | uuid                     |
| vespa_scores                 | student_id                  | uuid                     |
| vespa_scores                 | cycle                       | integer                  |
| vespa_scores                 | vision                      | integer                  |
| vespa_scores                 | effort                      | integer                  |
| vespa_scores                 | systems                     | integer                  |
| vespa_scores                 | practice                    | integer                  |
| vespa_scores                 | attitude                    | integer                  |
| vespa_scores                 | overall                     | integer                  |
| vespa_scores                 | completion_date             | date                     |
| vespa_scores                 | academic_year               | character varying        |
| vespa_scores                 | created_at                  | timestamp with time zone |