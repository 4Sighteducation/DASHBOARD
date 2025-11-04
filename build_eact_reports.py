#!/usr/bin/env python3
"""
Generate E-ACT Academy Trust Cycle 1 Baseline VESPA Reports
- 1 Executive Summary (Trust-wide)
- 6 Individual School Reports with Questionnaire Insights
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from datetime import datetime
from scipy import stats as scipy_stats
from pathlib import Path

# National averages from November 4th 2025 data drop
NATIONAL_AVERAGES = {
    'Vision': 6.36,
    'Effort': 5.94,
    'Systems': 5.68,
    'Practice': 5.93,
    'Attitude': 5.79,
    'Overall': 5.94
}

# National distributions (percentages)
NATIONAL_DISTRIBUTIONS = {
    'Vision': {1: 1.07, 2: 3.41, 3: 9.35, 4: 8.13, 5: 9.17, 6: 21.78, 7: 12.05, 8: 18.31, 9: 7.52, 10: 9.20},
    'Effort': {1: 2.73, 2: 2.60, 3: 13.01, 4: 10.20, 5: 13.33, 6: 15.18, 7: 14.91, 8: 11.24, 9: 13.74, 10: 3.04},
    'Systems': {1: 3.12, 2: 4.57, 3: 10.22, 4: 14.89, 5: 10.16, 6: 22.21, 7: 10.07, 8: 15.48, 9: 5.21, 10: 4.06},
    'Practice': {1: 1.95, 2: 3.84, 3: 7.92, 4: 12.76, 5: 19.50, 6: 10.28, 7: 17.83, 8: 13.31, 9: 7.60, 10: 5.01},
    'Attitude': {1: 2.48, 2: 5.96, 3: 10.21, 4: 9.60, 5: 12.10, 6: 20.95, 7: 14.29, 8: 13.81, 9: 7.33, 10: 3.23},
    'Overall': {1: 0.30, 2: 1.32, 3: 5.83, 4: 12.98, 5: 19.11, 6: 22.46, 7: 20.33, 8: 11.35, 9: 5.12, 10: 1.19}
}

COLORS = {
    'Vision': '#e59437',
    'Effort': '#86b4f0',
    'Systems': '#72cb44',
    'Practice': '#7f31a4',
    'Attitude': '#f032e6',
    'Overall': '#ffd700'
}

# School logo paths (relative to script location)
SCHOOL_LOGOS = {
    'North Birmingham Academy': 'E-ACT-North-Birmingham-Academy_Logo-Stacked_Full-Colour_Web.png',
    'Montpelier High School': 'montpelier-high-school-logo.png',
    'Ousedale School': '51A051D3872FD2795D5CC7FE41DD6E46.png',
    'Crest Academy': 'crest-logo.png',
    'West Walsall Academy': 'R (1).png',
    'Daventry 6th Form': 'E-ACT-Daventry-Sixth-Form_Logo-Stacked_Full-Colour_Web.png'
}

# Statement to category mapping (from Hartpury report)
STATEMENT_MAPPING = {
    "I've worked out the next steps in my life": 'Vision',
    "I plan and organise my time to get my work done": 'Systems',
    "I give a lot of attention to my career planning": 'Vision',
    "I complete all my homework on time": 'Systems',
    "No matter who you are, you can change your intelligence a lot": 'Attitude',
    "I use all my independent study time effectively": 'Effort',
    "I test myself on important topics until I remember them": 'Practice',
    "I have a positive view of myself": 'Attitude',
    "I am a hard working student": 'Effort',
    "I am confident in my academic ability": 'Attitude',
    "I always meet deadlines ": 'Systems',
    "I spread out my revision,  rather than cramming at the last minute.": 'Practice',
    "I don't let a poor test/assessment result get me down for too long": 'Attitude',
    "I strive to achieve the goals I set for myself": 'Vision',
    "I summarise important information in diagrams, tables or lists": 'Practice',
    "I enjoy learning new things ": 'Vision',
    "I'm not happy unless my work is the best it can be": 'Effort',
    "I take good notes in class which are useful for revision": 'Systems',
    "When revising I mix different kinds of topics/subjects in one study session": 'Practice',
    "I feel I can cope with the pressure at school/college/University": 'Attitude',
    "I work as hard as I can in most classes": 'Effort',
    "My books/files are organised": 'Systems',
    "I study by explaining difficult topics outloud": 'Practice',
    "I'm happy to ask questions in front of a group.": 'Attitude',
    "When revising, I work under timed conditions answering exam-style questions": 'Practice',
    "Your intelligence is something about you that you can change very much": 'Attitude',
    "I like hearing feedback about how I can improve": 'Attitude',
    "I can control my nerves in tests/practical assessments.": 'Attitude',
    "I know what grades I want to achieve": 'Vision',
    # Outcome questions
    "I have the support I need to achieve this year?": 'Outcome',
    " I feel equipped to face the study and revision challenges this year?": 'Outcome',
    " I am confident I will achieve my potential in my final exams?": 'Outcome'
}

# 12 Questionnaire Insights mapping
QUESTIONNAIRE_INSIGHTS = {
    'growth_mindset': {
        'title': 'Growth Mindset',
        'icon': '🌱',
        'color': '#10b981',
        'questions': [
            "No matter who you are, you can change your intelligence a lot",
            "Your intelligence is something about you that you can change very much",
            "I like hearing feedback about how I can improve",
            "I enjoy learning new things "
        ]
    },
    'academic_momentum': {
        'title': 'Academic Momentum',
        'icon': '🚀',
        'color': '#3b82f6',
        'questions': [
            "I strive to achieve the goals I set for myself",
            "I enjoy learning new things ",
            "I'm not happy unless my work is the best it can be",
            "I am a hard working student"
        ]
    },
    'resilience_factor': {
        'title': 'Resilience Factor',
        'icon': '💪',
        'color': '#8b5cf6',
        'questions': [
            "I don't let a poor test/assessment result get me down for too long",
            "I like hearing feedback about how I can improve",
            "I have a positive view of myself"
        ]
    },
    'time_management': {
        'title': 'Time Management',
        'icon': '⏰',
        'color': '#f59e0b',
        'questions': [
            "I plan and organise my time to get my work done",
            "I complete all my homework on time",
            "I always meet deadlines "
        ]
    },
    'support_help_seeking': {
        'title': 'Support & Help-Seeking',
        'icon': '🤝',
        'color': '#ec4899',
        'questions': [
            "I have the support I need to achieve this year?",
            "I'm happy to ask questions in front of a group.",
            "I like hearing feedback about how I can improve"
        ]
    },
    'revision_readiness': {
        'title': 'Revision Readiness',
        'icon': '📖',
        'color': '#06b6d4',
        'questions': [
            " I feel equipped to face the study and revision challenges this year?",
            "I test myself on important topics until I remember them",
            "I spread out my revision,  rather than cramming at the last minute.",
            "I take good notes in class which are useful for revision"
        ]
    },
    'study_strategies': {
        'title': 'Study Strategies',
        'icon': '📚',
        'color': '#14b8a6',
        'questions': [
            "I test myself on important topics until I remember them",
            "I spread out my revision,  rather than cramming at the last minute.",
            "I summarise important information in diagrams, tables or lists",
            "I take good notes in class which are useful for revision"
        ]
    },
    'exam_confidence': {
        'title': 'Exam Confidence',
        'icon': '⭐',
        'color': '#fbbf24',
        'questions': [
            " I am confident I will achieve my potential in my final exams?",
            "I am confident in my academic ability",
            "I can control my nerves in tests/practical assessments."
        ]
    },
    'organization_materials': {
        'title': 'Organization & Materials',
        'icon': '📦',
        'color': '#a855f7',
        'questions': [
            "My books/files are organised",
            "I take good notes in class which are useful for revision"
        ]
    },
    'vision_purpose': {
        'title': 'Vision & Purpose',
        'icon': '🎯',
        'color': '#ef4444',
        'questions': [
            "I've worked out the next steps in my life",
            "I give a lot of attention to my career planning",
            "I know what grades I want to achieve"
        ]
    },
    'stress_management': {
        'title': 'Stress Management',
        'icon': '😌',
        'color': '#84cc16',
        'questions': [
            "I feel I can cope with the pressure at school/college/University",
            "I can control my nerves in tests/practical assessments.",
            "I'm happy to ask questions in front of a group."
        ]
    },
    'active_learning': {
        'title': 'Active Learning',
        'icon': '🎓',
        'color': '#06b6d4',
        'questions': [
            "I study by explaining difficult topics outloud",
            "When revising I mix different kinds of topics/subjects in one study session",
            "I test myself on important topics until I remember them"
        ]
    }
}

def load_data(csv_path):
    """Load and clean E-ACT Cycle 1 data"""
    print("Loading E-ACT Academy Trust data...")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    
    # Filter for Cycle 1 only and exclude Bourne End Academy
    df_cycle1 = df[(df['Cycle'] == 1) & (~df['VESPA Customer'].str.contains('Bourne End', na=False))].copy()
    
    # Keep only rows with valid VESPA scores
    vespa_cols = ['vScale', 'eScale', 'sScale', 'pScale', 'aScale', 'oScale']
    df_cycle1 = df_cycle1[df_cycle1[vespa_cols].notna().all(axis=1)]
    
    print(f"✅ Loaded {len(df_cycle1)} students with complete Cycle 1 VESPA data")
    print(f"   Schools: {df_cycle1['VESPA Customer'].nunique()}")
    print(f"   Mean Overall: {df_cycle1['oScale'].mean():.2f}")
    
    return df_cycle1

def calculate_eri(df):
    """Calculate Exam Readiness Index from 3 outcome questions"""
    outcome_cols = [
        "I have the support I need to achieve this year?",
        " I feel equipped to face the study and revision challenges this year?",
        " I am confident I will achieve my potential in my final exams?"
    ]
    
    # Get values for all 3 outcome questions
    outcome_values = df[outcome_cols].values
    
    # Calculate mean across the 3 questions for each student, then average
    student_eris = np.nanmean(outcome_values, axis=1)
    
    # Return mean ERI
    return np.nanmean(student_eris)

def calculate_insight_percentage(df, insight_questions):
    """Calculate percentage agreement (4s and 5s) for questionnaire insight"""
    total_responses = 0
    agreement_count = 0
    
    for question in insight_questions:
        if question in df.columns:
            values = df[question].dropna()
            total_responses += len(values)
            agreement_count += len(values[values >= 4])
    
    if total_responses == 0:
        return 0.0, 0
    
    percentage = (agreement_count / total_responses) * 100
    return percentage, total_responses

def calculate_all_insights(df):
    """Calculate all 12 questionnaire insights"""
    insights = []
    
    for insight_id, insight_config in QUESTIONNAIRE_INSIGHTS.items():
        percentage, n_responses = calculate_insight_percentage(df, insight_config['questions'])
        
        insights.append({
            'id': insight_id,
            'title': insight_config['title'],
            'icon': insight_config['icon'],
            'color': insight_config['color'],
            'percentage': percentage,
            'n': n_responses
        })
    
    return insights

def calculate_distribution(series):
    """Calculate percentage distribution for scores 1-10"""
    total = len(series)
    distribution = {}
    for score in range(1, 11):
        count = (series.round() == score).sum()
        distribution[score] = (count / total * 100) if total > 0 else 0
    return distribution

def create_score_distribution_chart(df, dimension, color, col_name):
    """Create distribution chart comparing to national"""
    values = df[col_name].dropna()
    if len(values) == 0:
        return None
        
    dist = calculate_distribution(values)
    
    college_pct = [dist[i] for i in range(1, 11)]
    national_pct = [NATIONAL_DISTRIBUTIONS[dimension][i] for i in range(1, 11)]
    
    fig = go.Figure()
    
    # School bars
    fig.add_trace(go.Bar(
        x=list(range(1, 11)),
        y=college_pct,
        name='School',
        marker_color=color,
        opacity=0.7,
        showlegend=True
    ))
    
    # National line
    fig.add_trace(go.Scatter(
        x=list(range(1, 11)),
        y=national_pct,
        name='National',
        line=dict(color='red', width=2),
        marker=dict(size=6),
        mode='lines+markers',
        showlegend=True
    ))
    
    # Add mean scores annotation
    college_mean = values.mean()
    national_mean = NATIONAL_AVERAGES[dimension]
    
    fig.add_annotation(
        x=5.5,
        y=max(college_pct + national_pct) * 1.05,
        text=f"School: {college_mean:.1f}<br>National: {national_mean:.1f}",
        showarrow=False,
        font=dict(size=10)
    )
    
    fig.update_layout(
        title=f'{dimension} Score Distribution - Cycle 1',
        xaxis=dict(title='Score', range=[0.5, 10.5]),
        yaxis=dict(title='Percentage (%)'),
        height=400,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        paper_bgcolor='white',
        plot_bgcolor='rgba(240,240,240,0.3)'
    )
    
    return fig

def generate_executive_summary(df):
    """Generate Trust-wide Executive Summary HTML Report"""
    print("\n" + "="*80)
    print("GENERATING E-ACT TRUST EXECUTIVE SUMMARY")
    print("="*80)
    
    # Overall statistics
    overall_stats = {
        'n_students': len(df),
        'n_schools': df['VESPA Customer'].nunique(),
        'vision': df['vScale'].mean(),
        'effort': df['eScale'].mean(),
        'systems': df['sScale'].mean(),
        'practice': df['pScale'].mean(),
        'attitude': df['aScale'].mean(),
        'overall': df['oScale'].mean(),
        'eri': calculate_eri(df)
    }
    
    print(f"\nOverall: {overall_stats['n_students']} students, {overall_stats['n_schools']} schools")
    print(f"Mean scores - V:{overall_stats['vision']:.2f} E:{overall_stats['effort']:.2f} S:{overall_stats['systems']:.2f} P:{overall_stats['practice']:.2f} A:{overall_stats['attitude']:.2f} O:{overall_stats['overall']:.2f}")
    print(f"Exam Readiness Index: {overall_stats['eri']:.2f}")
    
    # School statistics
    print("\nCalculating school statistics...")
    school_stats = []
    for school in df['VESPA Customer'].dropna().unique():
        school_df = df[df['VESPA Customer'] == school]
        n = len(school_df)
        
        school_stats.append({
            'school': school,
            'n': n,
            'vision': school_df['vScale'].mean(),
            'effort': school_df['eScale'].mean(),
            'systems': school_df['sScale'].mean(),
            'practice': school_df['pScale'].mean(),
            'attitude': school_df['aScale'].mean(),
            'overall': school_df['oScale'].mean(),
            'eri': calculate_eri(school_df)
        })
    
    school_stats = sorted(school_stats, key=lambda x: x['overall'], reverse=True)
    print(f"   {len(school_stats)} schools analyzed")
    
    # Year Group statistics
    print("\nCalculating year group statistics...")
    year_group_stats = []
    for year_group in [12, 13]:
        yg_df = df[df['Year Gp'] == year_group]
        if len(yg_df) >= 10:
            year_group_stats.append({
                'year_group': year_group,
                'n': len(yg_df),
                'vision': yg_df['vScale'].mean(),
                'effort': yg_df['eScale'].mean(),
                'systems': yg_df['sScale'].mean(),
                'practice': yg_df['pScale'].mean(),
                'attitude': yg_df['aScale'].mean(),
                'overall': yg_df['oScale'].mean(),
                'eri': calculate_eri(yg_df)
            })
    
    year_group_stats = sorted(year_group_stats, key=lambda x: x['overall'], reverse=True)
    print(f"   {len(year_group_stats)} year groups analyzed")
    
    # Generate HTML
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EACT_Trust_Executive_Summary_{timestamp}.html"
    
    html = build_executive_summary_html(overall_stats, school_stats, year_group_stats, df)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n{'='*80}")
    print(f"✅ EXECUTIVE SUMMARY GENERATED")
    print(f"{'='*80}")
    print(f"Filename: {filename}")
    print(f"{'='*80}\n")
    
    return filename

def build_executive_summary_html(overall, schools, year_groups, df):
    """Build the Executive Summary HTML document"""
    report_date = datetime.now().strftime("%B %d, %Y")
    
    # Determine strongest/weakest dimensions
    dims = ['vision', 'effort', 'systems', 'practice', 'attitude']
    dim_scores = {d: overall[d] for d in dims}
    strongest_dim = max(dim_scores, key=dim_scores.get)
    weakest_dim = min(dim_scores, key=dim_scores.get)
    
    # Top performing school
    top_school = schools[0]
    
    # Calculate performance vs national
    overall_vs_nat = overall['overall'] - NATIONAL_AVERAGES['Overall']
    overall_status = "above" if overall_vs_nat > 0.1 else "in line with" if overall_vs_nat > -0.1 else "below"
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E-ACT Trust - VESPA Cycle 1 Baseline Executive Summary</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        {get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        {generate_header(report_date, "E-ACT Academy Trust", "Executive Summary", show_logo=True)}
        {generate_exec_summary_content(overall, schools, year_groups, strongest_dim, weakest_dim, overall_status)}
        {generate_baseline_overview(overall)}
        {generate_school_comparison_section(schools, overall)}
        {generate_year_group_section(year_groups, "Trust")}
        {generate_eri_section(overall, schools, year_groups)}
        {generate_footer("E-ACT Academy Trust")}
    </div>
</body>
</html>
"""
    
    return html

def generate_individual_school_report(school_name, school_df, overall_df):
    """Generate detailed individual school report with Questionnaire Insights"""
    print(f"\n{'='*80}")
    print(f"GENERATING REPORT FOR {school_name.upper()}")
    print(f"{'='*80}")
    
    # Overall statistics for this school
    school_stats = {
        'n_students': len(school_df),
        'vision': school_df['vScale'].mean(),
        'effort': school_df['eScale'].mean(),
        'systems': school_df['sScale'].mean(),
        'practice': school_df['pScale'].mean(),
        'attitude': school_df['aScale'].mean(),
        'overall': school_df['oScale'].mean(),
        'eri': calculate_eri(school_df)
    }
    
    print(f"Students: {school_stats['n_students']}")
    print(f"Overall Score: {school_stats['overall']:.2f}")
    print(f"ERI: {school_stats['eri']:.2f}")
    
    # Year Group statistics
    year_group_stats = []
    for year_group in [12, 13]:
        yg_df = school_df[school_df['Year Gp'] == year_group]
        if len(yg_df) >= 5:
            year_group_stats.append({
                'year_group': year_group,
                'n': len(yg_df),
                'vision': yg_df['vScale'].mean(),
                'effort': yg_df['eScale'].mean(),
                'systems': yg_df['sScale'].mean(),
                'practice': yg_df['pScale'].mean(),
                'attitude': yg_df['aScale'].mean(),
                'overall': yg_df['oScale'].mean(),
                'eri': calculate_eri(yg_df)
            })
    
    # Group statistics (only groups with n >= 5)
    group_stats = []
    if 'Group' in school_df.columns:
        for group in school_df['Group'].dropna().unique():
            group_df = school_df[school_df['Group'] == group]
            if len(group_df) >= 5:
                group_stats.append({
                    'group': group,
                    'n': len(group_df),
                    'vision': group_df['vScale'].mean(),
                    'effort': group_df['eScale'].mean(),
                    'systems': group_df['sScale'].mean(),
                    'practice': group_df['pScale'].mean(),
                    'attitude': group_df['aScale'].mean(),
                    'overall': group_df['oScale'].mean(),
                    'eri': calculate_eri(group_df)
                })
        group_stats = sorted(group_stats, key=lambda x: x['overall'], reverse=True)
    
    print(f"   Year Groups: {len(year_group_stats)}")
    print(f"   Groups (n≥5): {len(group_stats)}")
    
    # Calculate 12 Questionnaire Insights
    insights = calculate_all_insights(school_df)
    print(f"   Calculated {len(insights)} Questionnaire Insights")
    
    # Generate HTML
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = school_name.replace(' ', '_').replace('/', '_')
    filename = f"EACT_{safe_name}_Cycle1_Baseline_{timestamp}.html"
    
    html = build_school_report_html(school_name, school_stats, year_group_stats, group_stats, insights, school_df)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ REPORT GENERATED: {filename}")
    
    return filename

def build_school_report_html(school_name, stats, year_groups, groups, insights, df):
    """Build individual school report HTML"""
    report_date = datetime.now().strftime("%B %d, %Y")
    
    # Determine strongest/weakest dimensions
    dims = ['vision', 'effort', 'systems', 'practice', 'attitude']
    dim_scores = {d: stats[d] for d in dims}
    strongest_dim = max(dim_scores, key=dim_scores.get)
    weakest_dim = min(dim_scores, key=dim_scores.get)
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{school_name} - VESPA Cycle 1 Baseline Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        {get_css_styles()}
        {get_insights_css()}
    </style>
</head>
<body>
    <div class="container">
        {generate_header(report_date, school_name, "VESPA Cycle 1 Baseline Report", show_logo=False, school_name=school_name)}
        {generate_school_exec_summary(stats, strongest_dim, weakest_dim, school_name)}
        {generate_baseline_overview(stats)}
        {generate_eri_detail_section(stats, school_name)}
        {generate_insights_section(insights, school_name)}
        {generate_year_group_section(year_groups, school_name) if year_groups else ""}
        {generate_group_section(groups, stats, school_name) if groups else ""}
        {generate_distributions_section(df, school_name)}
        {generate_recommendations_section(stats, insights, strongest_dim, weakest_dim, school_name)}
        {generate_footer(school_name)}
    </div>
</body>
</html>
"""
    
    return html

def get_css_styles():
    """Return CSS styles for the reports"""
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .report-header {
            background: white;
            border-radius: 15px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .executive-summary, .section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .section h2, .executive-summary h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .section h3 {
            color: #764ba2;
            margin: 20px 0 10px 0;
            font-size: 1.4em;
        }
        
        .key-insights {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-card h4 {
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
        }
        
        .stat-card small {
            font-size: 0.8em;
            opacity: 0.8;
            display: block;
            margin-top: 5px;
        }
        
        .chart-container {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .positive {
            color: #28a745;
            font-weight: bold;
        }
        
        .negative {
            color: #dc3545;
            font-weight: bold;
        }
        
        .neutral {
            color: #666;
            font-weight: bold;
        }
        
        .footer {
            text-align: center;
            padding: 30px;
            color: white;
            opacity: 0.9;
        }
        
        .eri-card {
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            color: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            margin: 20px 0;
        }
        
        .eri-value {
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .eri-description {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        @media print {
            @page {
                size: A4;
                margin: 12mm 8mm;
            }
            
            body {
                background: white !important;
            }
            
            .container {
                max-width: 100%;
                width: 190mm;
            }
            
            .report-header button {
                display: none !important;
            }
        }
    """

def get_insights_css():
    """Return CSS for Questionnaire Insights section"""
    return """
        .insights-section {
            margin: 30px 0;
        }
        
        .insights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 25px;
        }
        
        .insight-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            border-left: 4px solid #667eea;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .insight-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .insight-card.excellent {
            border-left-color: #10b981;
            background: linear-gradient(to right, rgba(16, 185, 129, 0.05), white);
        }
        
        .insight-card.good {
            border-left-color: #3b82f6;
            background: linear-gradient(to right, rgba(59, 130, 246, 0.05), white);
        }
        
        .insight-card.average {
            border-left-color: #f59e0b;
            background: linear-gradient(to right, rgba(245, 158, 11, 0.05), white);
        }
        
        .insight-card.poor {
            border-left-color: #ef4444;
            background: linear-gradient(to right, rgba(239, 68, 68, 0.05), white);
        }
        
        .insight-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 15px;
        }
        
        .insight-icon {
            font-size: 2em;
        }
        
        .insight-title {
            font-size: 1.1em;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .insight-percentage {
            font-size: 2.5em;
            font-weight: bold;
            text-align: center;
            margin: 15px 0;
        }
        
        .insight-percentage.excellent {
            color: #10b981;
        }
        
        .insight-percentage.good {
            color: #3b82f6;
        }
        
        .insight-percentage.average {
            color: #f59e0b;
        }
        
        .insight-percentage.poor {
            color: #ef4444;
        }
        
        .insight-label {
            text-align: center;
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .insight-meta {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e0e0e0;
            font-size: 0.85em;
            color: #666;
            text-align: center;
        }
    """

def generate_header(report_date, org_name, subtitle, show_logo=False, school_name=None):
    """Generate report header"""
    logo_html = ""
    if show_logo:
        # Use E-ACT Trust logo for executive summary
        logo_html = """
            <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 20px;">
                <img src="https://schoolsweek.co.uk/wp-content/uploads/2018/08/e-act-1920x1017.png" 
                     alt="E-ACT Logo" 
                     style="height: 80px; object-fit: contain; max-width: 300px;">
            </div>
        """
    elif school_name and school_name in SCHOOL_LOGOS:
        # Use school-specific logo for individual reports
        logo_path = SCHOOL_LOGOS[school_name]
        logo_html = f"""
            <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 20px;">
                <img src="{logo_path}" 
                     alt="{school_name} Logo" 
                     style="height: 100px; object-fit: contain; max-width: 400px;">
            </div>
        """
    
    return f"""
        <div class="report-header">
            {logo_html}
            <h1 style="color: #667eea; margin-bottom: 10px; text-align: center;">{org_name}</h1>
            <h2 style="color: #764ba2; text-align: center;">{subtitle}</h2>
            <p class="report-date" style="text-align: center;">Generated: {report_date}</p>
            
            <div style="margin-top: 20px; text-align: center;">
                <button onclick="window.print();" style="
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    font-size: 1em;
                    font-weight: 600;
                    border-radius: 25px;
                    cursor: pointer;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                    transition: all 0.3s;
                " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(102, 126, 234, 0.4)';" 
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(102, 126, 234, 0.3)';">
                    Download as PDF
                </button>
            </div>
        </div>
"""

def generate_exec_summary_content(overall, schools, year_groups, strongest_dim, weakest_dim, overall_status):
    """Generate executive summary content section"""
    top_school = schools[0]
    
    # Year group insights
    yg_12 = next((yg for yg in year_groups if yg['year_group'] == 12), None)
    yg_13 = next((yg for yg in year_groups if yg['year_group'] == 13), None)
    
    yg_comparison = ""
    if yg_12 and yg_13:
        if yg_13['overall'] > yg_12['overall']:
            yg_comparison = f"Year 13 students demonstrate stronger baseline performance ({yg_13['overall']:.2f}) compared to Year 12 ({yg_12['overall']:.2f}), reflecting their additional year of experience and maturity."
        else:
            yg_comparison = f"Year 12 students show strong baseline engagement ({yg_12['overall']:.2f}), matching or exceeding Year 13 performance ({yg_13['overall']:.2f})."
    
    html = f"""
        <div class="executive-summary">
            <h2>Executive Summary</h2>
            <p>This comprehensive VESPA Cycle 1 baseline analysis examines student mindset and study skills 
            across the <strong>E-ACT Academy Trust</strong>, encompassing <strong>{overall['n_students']:,} students</strong> 
            from <strong>{overall['n_schools']} schools</strong>. This baseline assessment establishes the starting point 
            for tracking student development throughout the 2025/26 academic year.</p>
            
            <p style="margin-top: 15px;"><strong>Overall Performance:</strong> Trust students score {overall_status} national 
            average ({overall['overall']:.2f} vs {NATIONAL_AVERAGES['Overall']}), demonstrating {"strong" if overall['overall'] > NATIONAL_AVERAGES['Overall'] else "solid"} 
            engagement with learning mindsets and study skills at this baseline stage.</p>
            
            <p style="margin-top: 15px;"><strong>Exam Readiness Index:</strong> The Trust's baseline ERI of {overall['eri']:.2f} 
            indicates that students feel {"well-prepared" if overall['eri'] >= 3.5 else "moderately prepared" if overall['eri'] >= 3.0 else "in need of additional support"} 
            for their exam challenges ahead.</p>
            
            <p style="margin-top: 15px;"><strong>Looking Ahead:</strong> This Cycle 1 baseline will be compared against Cycle 2 
            (mid-year, January) and Cycle 3 (end-of-year). Typically, students experience a natural adjustment in Cycle 2 as 
            they engage with the realities of their courses, before showing strong growth and recovery by Cycle 3.</p>
            
            <div class="key-insights" style="margin-top: 25px;">
                <h3 style="color: #667eea; margin-bottom: 20px;">Key Baseline Findings</h3>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px;">
                    <div style="background: rgba(102, 126, 234, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Overall Baseline</h4>
                        <p>Students demonstrate {strongest_dim.title()} as their strongest dimension ({overall[strongest_dim]:.2f}), 
                        while {weakest_dim.title()} ({overall[weakest_dim]:.2f}) presents the primary development opportunity for the year ahead.</p>
                    </div>
                    
                    <div style="background: rgba(114, 203, 68, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #72cb44;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Top Performing School</h4>
                        <p>{top_school['school']} leads with {top_school['overall']:.2f} overall score (n={top_school['n']} students). 
                        Variation across schools indicates opportunities for peer learning and best practice sharing.</p>
                    </div>
                    
                    <div style="background: rgba(245, 158, 11, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Year Group Insights</h4>
                        <p>{yg_comparison}</p>
                    </div>
                    
                    <div style="background: rgba(251, 191, 36, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #fbbf24;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Exam Readiness</h4>
                        <p>Trust ERI of {overall['eri']:.2f} reflects students' perceived preparation for exam challenges. 
                        Individual school ERI ranges from {min(s['eri'] for s in schools):.2f} to {max(s['eri'] for s in schools):.2f}, 
                        highlighting areas for targeted support.</p>
                    </div>
                </div>
                
                <div style="margin-top: 25px; padding: 20px; background: linear-gradient(to right, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05)); border-radius: 8px;">
                    <h4 style="color: #2c3e50; margin-bottom: 12px;">Strategic Priorities for 2025/26</h4>
                    <ul style="margin: 0; padding-left: 25px; line-height: 1.8;">
                        <li><strong>Build on Strengths:</strong> Leverage strong {strongest_dim.title()} baseline ({overall[strongest_dim]:.2f}) across all schools</li>
                        <li><strong>Target Development:</strong> Focus interventions on {weakest_dim.title()} skills (current: {overall[weakest_dim]:.2f})</li>
                        <li><strong>Cross-School Collaboration:</strong> Facilitate sharing of best practices from {top_school['school']}</li>
                        <li><strong>Enhance Exam Readiness:</strong> Implement targeted support to improve ERI, particularly in schools scoring below 3.0</li>
                        <li><strong>Monitor Progress:</strong> Track Cycle 2 (January) to identify early intervention needs and celebrate growth</li>
                    </ul>
                </div>
            </div>
        </div>
"""
    return html

def generate_school_exec_summary(stats, strongest_dim, weakest_dim, school_name):
    """Generate executive summary for individual school report"""
    vs_national = stats['overall'] - NATIONAL_AVERAGES['Overall']
    status = "above" if vs_national > 0.1 else "in line with" if vs_national > -0.1 else "below"
    
    return f"""
        <div class="executive-summary">
            <h2>Executive Summary</h2>
            <p>This comprehensive VESPA Cycle 1 baseline analysis for <strong>{school_name}</strong> examines student mindset and study skills 
            across <strong>{stats['n_students']} students</strong>. This baseline assessment establishes the starting point for tracking 
            student development throughout the 2025/26 academic year.</p>
            
            <p style="margin-top: 15px;"><strong>Overall Performance:</strong> {school_name} students score {status} national 
            average ({stats['overall']:.2f} vs {NATIONAL_AVERAGES['Overall']}), demonstrating {"strong" if vs_national > 0 else "solid"} 
            engagement with learning mindsets and study skills.</p>
            
            <p style="margin-top: 15px;"><strong>Exam Readiness:</strong> The school's ERI of {stats['eri']:.2f} indicates 
            students feel {"confident and well-prepared" if stats['eri'] >= 4.0 else "adequately prepared" if stats['eri'] >= 3.5 else "moderately prepared" if stats['eri'] >= 3.0 else "in need of additional support"} 
            for their upcoming exams.</p>
            
            <p style="margin-top: 15px;"><strong>Key Strengths:</strong> Students demonstrate particular strength in {strongest_dim.title()} ({stats[strongest_dim]:.2f}), 
            while {weakest_dim.title()} ({stats[weakest_dim]:.2f}) presents an opportunity for targeted development.</p>
        </div>
"""

def generate_baseline_overview(stats):
    """Generate baseline overview section with comparison to national"""
    
    def compare_to_nat(score, dim_name):
        nat = NATIONAL_AVERAGES[dim_name]
        diff = score - nat
        if diff > 0.2:
            arrow, status, color = '↑', 'Above National', '#28a745'
        elif diff < -0.2:
            arrow, status, color = '↓', 'Below National', '#dc3545'
        else:
            arrow, status, color = '•', 'On Par', '#666'
        
        return f"""
            <div class="stat-card">
                <h4>{dim_name}</h4>
                <div class="value">{score:.2f}</div>
                <small>National: {nat}</small>
                <div style="margin-top: 8px; font-size: 0.85em;">
                    <span style="color: white;">{arrow} {status}</span>
                </div>
            </div>
        """
    
    html = f"""
        <div class="section">
            <h2>📊 Cycle 1 Baseline Overview</h2>
            <p style="margin-bottom: 20px;">
                Baseline VESPA scores for {stats['n_students']} students compared to national averages.
                This establishes the starting point for measuring growth through Cycles 2 and 3.
            </p>
            
            <div class="stats-grid">
                {compare_to_nat(stats['vision'], 'Vision')}
                {compare_to_nat(stats['effort'], 'Effort')}
                {compare_to_nat(stats['systems'], 'Systems')}
                {compare_to_nat(stats['practice'], 'Practice')}
                {compare_to_nat(stats['attitude'], 'Attitude')}
                {compare_to_nat(stats['overall'], 'Overall')}
            </div>
        </div>
"""
    return html

def generate_school_comparison_section(schools, overall):
    """Generate school comparison section for executive summary"""
    
    # Generate school cards for ALL schools
    school_cards = ""
    for idx, school in enumerate(schools, 1):
        badge_color = '#28a745' if idx <= 2 else '#3b82f6' if idx <= 4 else '#667eea'
        
        school_cards += f"""
                <div style="background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border-top: 4px solid {badge_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="color: #2c3e50; margin: 0; font-size: 1.1em; max-width: 70%;">{school['school']}</h3>
                        <span style="background: {badge_color}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.9em; font-weight: 600;">#{idx}</span>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px;">
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(229,148,55,0.1), rgba(229,148,55,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #e59437; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Vision</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{school['vision']:.2f}</div>
                        </div>
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(134,180,240,0.1), rgba(134,180,240,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #5690d6; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Effort</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{school['effort']:.2f}</div>
                        </div>
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(114,203,68,0.1), rgba(114,203,68,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #72cb44; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Systems</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{school['systems']:.2f}</div>
                        </div>
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(127,49,164,0.1), rgba(127,49,164,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #7f31a4; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Practice</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{school['practice']:.2f}</div>
                        </div>
                    </div>
                    
                    <div style="padding: 12px; background: linear-gradient(45deg, rgba(240,50,230,0.1), rgba(240,50,230,0.05)); border-radius: 8px; text-align: center; margin-bottom: 15px;">
                        <div style="color: #f032e6; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Attitude</div>
                        <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{school['attitude']:.2f}</div>
                    </div>
                    
                    <div style="padding: 15px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 10px; text-align: center; color: white;">
                        <div style="font-size: 0.9em; font-weight: 600; opacity: 0.9; text-transform: uppercase;">Overall Score</div>
                        <div style="font-size: 2.5em; font-weight: bold; margin: 5px 0;">{school['overall']:.2f}</div>
                        <div style="font-size: 0.8em; opacity: 0.8;">n = {school['n']} students | ERI: {school['eri']:.2f}</div>
                    </div>
                </div>
"""
    
    # Generate table rows for ALL schools
    table_rows = ""
    for school in schools:
        def indicator(score, nat):
            if score > nat + 0.2:
                return f'<span style="color: #28a745; font-weight: 600;">↑ {score:.2f}</span>'
            elif score < nat - 0.2:
                return f'<span style="color: #dc3545; font-weight: 600;">↓ {score:.2f}</span>'
            else:
                return f'<span style="color: #666; font-weight: 600;">• {score:.2f}</span>'
        
        row_bg = '#f8f9fa' if schools.index(school) % 2 == 0 else '#ffffff'
        
        table_rows += f"""
                    <tr style="background: {row_bg}; border-bottom: 1px solid #e9ecef;">
                        <td style="padding: 14px; font-weight: 600; color: #2c3e50;">{school['school']} (n={school['n']})</td>
                        <td style="padding: 14px; text-align: center;">{indicator(school['vision'], NATIONAL_AVERAGES['Vision'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(school['effort'], NATIONAL_AVERAGES['Effort'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(school['systems'], NATIONAL_AVERAGES['Systems'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(school['practice'], NATIONAL_AVERAGES['Practice'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(school['attitude'], NATIONAL_AVERAGES['Attitude'])}</td>
                        <td style="padding: 14px; text-align: center; background: rgba(102, 126, 234, 0.05); font-size: 1.1em;">{indicator(school['overall'], NATIONAL_AVERAGES['Overall'])}</td>
                        <td style="padding: 14px; text-align: center; font-weight: bold;">{school['eri']:.2f}</td>
                    </tr>
"""
    
    html = f"""
        <div class="section" style="padding: 40px;">
            <h2 style="color: #2c3e50; font-size: 2.2em; margin-bottom: 30px; border-bottom: 3px solid #667eea; padding-bottom: 15px;">
                School Performance Comparison - Baseline
            </h2>
            <p style="font-size: 1.2em; color: #555; margin-bottom: 40px;">
                Comprehensive VESPA performance metrics across all Trust schools based on Cycle 1 baseline assessment.
            </p>
            
            <div class="school-cards-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 25px; margin-bottom: 50px;">
                {school_cards}
            </div>
            
            <h3 style="color: #2c3e50; margin-top: 50px; margin-bottom: 15px; font-size: 1.5em;">Detailed Performance Matrix</h3>
            <p style="font-size: 0.95em; color: #666; margin-bottom: 15px;">Complete comparison showing all schools side-by-side.</p>
            <div style="overflow-x: auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <table style="width: 100%; min-width: 800px; border-collapse: separate; border-spacing: 0; background: white;">
                    <thead>
                        <tr>
                            <th style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 18px; text-align: left;">School</th>
                            <th style="background: #e59437; color: white; padding: 18px; text-align: center;">VISION</th>
                            <th style="background: #5690d6; color: white; padding: 18px; text-align: center;">EFFORT</th>
                            <th style="background: #72cb44; color: white; padding: 18px; text-align: center;">SYSTEMS</th>
                            <th style="background: #7f31a4; color: white; padding: 18px; text-align: center;">PRACTICE</th>
                            <th style="background: #f032e6; color: white; padding: 18px; text-align: center;">ATTITUDE</th>
                            <th style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 18px; text-align: center; font-weight: bold;">OVERALL</th>
                            <th style="background: #fbbf24; color: white; padding: 18px; text-align: center; font-weight: bold;">ERI</th>
                        </tr>
                    </thead>
                    <tbody>
                    {table_rows}
                    
                    <tr style="background: linear-gradient(135deg, #667eea, #764ba2); color: white;">
                        <td style="padding: 16px; font-weight: bold;">TRUST AVERAGE</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['vision']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['effort']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['systems']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['practice']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['attitude']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold; font-size: 1.1em;">{overall['overall']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold; font-size: 1.1em;">{overall['eri']:.2f}</td>
                    </tr>
                    </tbody>
                </table>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; gap: 30px; flex-wrap: wrap;">
                <span style="font-weight: 600; color: #2c3e50;">Performance Indicators vs National:</span>
                <span style="color: #28a745;">↑ Above National (+0.2)</span>
                <span style="color: #666;">• On Par with National (±0.2)</span>
                <span style="color: #dc3545;">↓ Below National (-0.2)</span>
            </div>
        </div>
"""
    return html

def generate_year_group_section(year_groups, org_name):
    """Generate year group analysis section"""
    if not year_groups or len(year_groups) == 0:
        return ""
    
    # Generate year group cards
    yg_cards = ""
    for idx, yg in enumerate(year_groups, 1):
        badge_color = '#28a745' if idx == 1 else '#667eea'
        
        yg_cards += f"""
                <div class="stat-card">
                    <h4>Year {yg['year_group']}</h4>
                    <div class="value">{yg['overall']:.2f}</div>
                    <small>n={yg['n']} students</small>
                    <div style="margin-top: 8px; font-size: 0.75em;">
                        Rank: #{idx} of {len(year_groups)} | ERI: {yg['eri']:.2f}
                    </div>
                </div>
"""
    
    # Generate table rows
    table_rows = ""
    for yg in year_groups:
        row_bg = '#f8f9fa' if year_groups.index(yg) % 2 == 0 else '#ffffff'
        
        table_rows += f"""
                    <tr style="background: {row_bg};">
                        <td style="padding: 12px; font-weight: 600;">Year {yg['year_group']}</td>
                        <td style="padding: 12px; text-align: center;">{yg['n']}</td>
                        <td style="padding: 12px; text-align: center;">{yg['vision']:.2f}</td>
                        <td style="padding: 12px; text-align: center;">{yg['effort']:.2f}</td>
                        <td style="padding: 12px; text-align: center;">{yg['systems']:.2f}</td>
                        <td style="padding: 12px; text-align: center;">{yg['practice']:.2f}</td>
                        <td style="padding: 12px; text-align: center;">{yg['attitude']:.2f}</td>
                        <td style="padding: 12px; text-align: center; font-weight: bold; background: rgba(102, 126, 234, 0.05);">{yg['overall']:.2f}</td>
                        <td style="padding: 12px; text-align: center; font-weight: bold;">{yg['eri']:.2f}</td>
                    </tr>
"""
    
    html = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                YEAR GROUP ANALYSIS
            </h1>
        </div>
        
        <div class="section">
            <h2>📚 VESPA Scores by Year Group</h2>
            <p style="margin-bottom: 20px;">
                Analysis of VESPA baseline scores across different year groups within {org_name}.
                Year groups are compared to understand cohort-specific patterns.
            </p>
            
            <h3>Year Group Performance Overview</h3>
            <div class="stats-grid">
                {yg_cards}
            </div>
            
            <h3>Detailed Year Group Comparison</h3>
            <table>
                <thead>
                    <tr>
                        <th>Year Group</th>
                        <th style="text-align: center;">Students</th>
                        <th style="text-align: center;">Vision</th>
                        <th style="text-align: center;">Effort</th>
                        <th style="text-align: center;">Systems</th>
                        <th style="text-align: center;">Practice</th>
                        <th style="text-align: center;">Attitude</th>
                        <th style="text-align: center;">Overall</th>
                        <th style="text-align: center;">ERI</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h4>Year Group Analysis Insights</h4>
                <ul style="margin-top: 10px;">
                    <li><strong>Highest Performing:</strong> Year {year_groups[0]['year_group']} leads with {year_groups[0]['overall']:.2f} overall score (n={year_groups[0]['n']} students)</li>
                    <li><strong>Development Focus:</strong> Use baseline differences to tailor intervention strategies by year group</li>
                    <li><strong>ERI Comparison:</strong> Year {year_groups[0]['year_group']} ERI: {year_groups[0]['eri']:.2f}, Year {year_groups[-1]['year_group']} ERI: {year_groups[-1]['eri']:.2f}</li>
                </ul>
            </div>
        </div>
"""
    return html

def generate_eri_section(overall, schools, year_groups):
    """Generate Exam Readiness Index section for executive summary"""
    
    # Find schools with highest/lowest ERI
    schools_by_eri = sorted(schools, key=lambda x: x['eri'], reverse=True)
    highest_eri_school = schools_by_eri[0]
    lowest_eri_school = schools_by_eri[-1]
    
    html = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #fbbf24; padding-bottom: 10px; margin: 0 auto 30px; max-width: 600px;">
                EXAM READINESS INDEX (ERI)
            </h1>
        </div>
        
        <div class="section">
            <h2>⭐ Exam Readiness Index Analysis</h2>
            <p style="margin-bottom: 20px;">
                The Exam Readiness Index (ERI) is calculated from three outcome questions measuring students' perceived preparation, 
                support, and confidence for their exams. Scores range from 1-5, with higher scores indicating greater readiness.
            </p>
            
            <div class="eri-card">
                <div style="font-size: 1.2em; opacity: 0.9;">Trust-Wide Exam Readiness Index</div>
                <div class="eri-value">{overall['eri']:.2f}</div>
                <div class="eri-description">
                    {"Excellent - Students feel well-prepared and confident" if overall['eri'] >= 4.0 else 
                     "Good - Students feel adequately prepared" if overall['eri'] >= 3.5 else 
                     "Moderate - Room for improvement in exam preparation support" if overall['eri'] >= 3.0 else
                     "Area of Focus - Students need additional exam preparation support"}
                </div>
                <div style="margin-top: 15px; font-size: 0.9em;">
                    Based on {overall['n_students']} student responses
                </div>
            </div>
            
            <h3>School ERI Comparison</h3>
            <table>
                <thead>
                    <tr>
                        <th>School</th>
                        <th style="text-align: center;">Students</th>
                        <th style="text-align: center;">Exam Readiness Index</th>
                        <th style="text-align: center;">Status</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for school in schools_by_eri:
        eri = school['eri']
        if eri >= 4.0:
            status = "Excellent"
            color = "#10b981"
        elif eri >= 3.5:
            status = "Good"
            color = "#3b82f6"
        elif eri >= 3.0:
            status = "Moderate"
            color = "#f59e0b"
        else:
            status = "Needs Support"
            color = "#ef4444"
        
        row_bg = '#f8f9fa' if schools_by_eri.index(school) % 2 == 0 else '#ffffff'
        
        html += f"""
                    <tr style="background: {row_bg};">
                        <td style="padding: 14px; font-weight: 600;">{school['school']}</td>
                        <td style="padding: 14px; text-align: center;">{school['n']}</td>
                        <td style="padding: 14px; text-align: center; font-size: 1.2em; font-weight: bold; color: {color};">{eri:.2f}</td>
                        <td style="padding: 14px; text-align: center;">
                            <span style="background: {color}20; color: {color}; padding: 5px 15px; border-radius: 20px; font-weight: 600;">{status}</span>
                        </td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h4>ERI Insights</h4>
                <ul style="margin-top: 10px;">
"""
    
    html += f"""
                    <li><strong>Highest ERI:</strong> {highest_eri_school['school']} ({highest_eri_school['eri']:.2f}) - Students feel most confident and prepared</li>
                    <li><strong>Focus Area:</strong> {lowest_eri_school['school']} ({lowest_eri_school['eri']:.2f}) - Consider additional exam preparation support</li>
                    <li><strong>Range:</strong> ERI scores range from {lowest_eri_school['eri']:.2f} to {highest_eri_school['eri']:.2f}, indicating variation in student readiness across schools</li>
                </ul>
            </div>
        </div>
"""
    
    return html

def generate_eri_detail_section(stats, school_name):
    """Generate detailed ERI section for individual school report"""
    eri = stats['eri']
    
    if eri >= 4.0:
        status = "Excellent"
        color = "#10b981"
        description = "Students feel highly confident and well-prepared for their exams"
    elif eri >= 3.5:
        status = "Good"
        color = "#3b82f6"
        description = "Students feel adequately prepared for their exam challenges"
    elif eri >= 3.0:
        status = "Moderate"
        color = "#f59e0b"
        description = "Room for improvement in exam preparation and student confidence"
    else:
        status = "Needs Support"
        color = "#ef4444"
        description = "Students require additional support and preparation for exams"
    
    html = f"""
        <div class="section">
            <h2>⭐ Exam Readiness Index</h2>
            <p style="margin-bottom: 20px;">
                The Exam Readiness Index (ERI) measures students' perceived preparation for exams based on three key questions:
                feeling supported, feeling equipped, and feeling confident about achieving their potential.
            </p>
            
            <div style="background: linear-gradient(135deg, {color}, {color}cc); color: white; padding: 40px; border-radius: 15px; text-align: center; margin: 30px 0;">
                <div style="font-size: 1.3em; opacity: 0.95; margin-bottom: 10px;">{school_name} Exam Readiness Index</div>
                <div style="font-size: 4em; font-weight: bold; margin: 20px 0;">{eri:.2f}</div>
                <div style="font-size: 1.2em; opacity: 0.9; margin-bottom: 10px;">{status}</div>
                <div style="font-size: 1em; opacity: 0.85;">{description}</div>
                <div style="margin-top: 20px; font-size: 0.9em; opacity: 0.8;">
                    National Average: {NATIONAL_AVERAGES.get('ERI', 3.5):.2f} | Based on {stats['n_students']} students
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h4>What the ERI Measures</h4>
                <ul style="margin-top: 10px; line-height: 1.8;">
                    <li><strong>Support:</strong> "I have the support I need to achieve this year"</li>
                    <li><strong>Preparation:</strong> "I feel equipped to face study and revision challenges"</li>
                    <li><strong>Confidence:</strong> "I am confident I will achieve my potential in my final exams"</li>
                </ul>
            </div>
        </div>
"""
    return html

def generate_insights_section(insights, school_name):
    """Generate 12 Questionnaire Insights section (styled like dashboard)"""
    
    # Sort insights by percentage (highest first)
    insights_sorted = sorted(insights, key=lambda x: x['percentage'], reverse=True)
    
    insight_cards = ""
    for insight in insights_sorted:
        pct = insight['percentage']
        
        # Determine rating class
        if pct >= 75:
            rating_class = "excellent"
        elif pct >= 60:
            rating_class = "good"
        elif pct >= 40:
            rating_class = "average"
        else:
            rating_class = "poor"
        
        insight_cards += f"""
            <div class="insight-card {rating_class}">
                <div class="insight-header">
                    <div class="insight-icon">{insight['icon']}</div>
                    <div class="insight-title">{insight['title']}</div>
                </div>
                <div class="insight-percentage {rating_class}">{pct:.1f}%</div>
                <div class="insight-label">Agreement</div>
                <div class="insight-meta">
                    n = {insight['n']//len(QUESTIONNAIRE_INSIGHTS[insight['id']]['questions'])} responses per question
                </div>
            </div>
"""
    
    html = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 600px;">
                QUESTIONNAIRE INSIGHTS
            </h1>
        </div>
        
        <div class="section insights-section">
            <h2>📊 12 Psychometric Insights</h2>
            <p style="margin-bottom: 20px;">
                These insights group related questions to measure key psychological factors that research shows 
                are crucial for academic success. Percentages represent students who agreed or strongly agreed (scores of 4-5).
            </p>
            
            <div style="margin: 25px 0; padding: 20px; background: linear-gradient(to right, #f8f9fa, #ffffff); border-radius: 10px; border-left: 4px solid #667eea;">
                <h4 style="color: #2c3e50; margin-bottom: 10px;">Understanding the Ratings</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                    <div style="padding: 10px; background: rgba(16, 185, 129, 0.1); border-radius: 5px; border-left: 3px solid #10b981;">
                        <strong style="color: #10b981;">75%+ Excellent</strong><br>
                        <small>Most students show positive indicators</small>
                    </div>
                    <div style="padding: 10px; background: rgba(59, 130, 246, 0.1); border-radius: 5px; border-left: 3px solid #3b82f6;">
                        <strong style="color: #3b82f6;">60-74% Good</strong><br>
                        <small>Majority positive, room for growth</small>
                    </div>
                    <div style="padding: 10px; background: rgba(245, 158, 11, 0.1); border-radius: 5px; border-left: 3px solid #f59e0b;">
                        <strong style="color: #f59e0b;">40-59% Average</strong><br>
                        <small>Mixed responses, needs attention</small>
                    </div>
                    <div style="padding: 10px; background: rgba(239, 68, 68, 0.1); border-radius: 5px; border-left: 3px solid #ef4444;">
                        <strong style="color: #ef4444;">&lt;40% Poor</strong><br>
                        <small>Significant area for improvement</small>
                    </div>
                </div>
            </div>
            
            <div class="insights-grid">
                {insight_cards}
            </div>
        </div>
"""
    return html

def generate_group_section(groups, school_stats, school_name):
    """Generate group-level analysis section"""
    if not groups or len(groups) == 0:
        return ""
    
    table_rows = ""
    for group in groups:
        row_bg = '#f8f9fa' if groups.index(group) % 2 == 0 else '#ffffff'
        
        def indicator(score, nat):
            if score > nat + 0.2:
                return f'<span style="color: #28a745; font-weight: 600;">↑ {score:.2f}</span>'
            elif score < nat - 0.2:
                return f'<span style="color: #dc3545; font-weight: 600;">↓ {score:.2f}</span>'
            else:
                return f'<span style="color: #666; font-weight: 600;">• {score:.2f}</span>'
        
        table_rows += f"""
                    <tr style="background: {row_bg};">
                        <td style="padding: 14px; font-weight: 600;">{group['group']}</td>
                        <td style="padding: 14px; text-align: center;">{group['n']}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(group['vision'], NATIONAL_AVERAGES['Vision'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(group['effort'], NATIONAL_AVERAGES['Effort'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(group['systems'], NATIONAL_AVERAGES['Systems'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(group['practice'], NATIONAL_AVERAGES['Practice'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(group['attitude'], NATIONAL_AVERAGES['Attitude'])}</td>
                        <td style="padding: 14px; text-align: center; font-weight: bold; background: rgba(102, 126, 234, 0.05);">{indicator(group['overall'], NATIONAL_AVERAGES['Overall'])}</td>
                        <td style="padding: 14px; text-align: center; font-weight: bold;">{group['eri']:.2f}</td>
                    </tr>
"""
    
    html = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                GROUP ANALYSIS
            </h1>
        </div>
        
        <div class="section">
            <h2>👥 Performance by Group</h2>
            <p style="margin-bottom: 20px;">
                Detailed analysis of VESPA baseline scores across different tutorial/mentor groups within {school_name}.
                Only groups with 5 or more students are included in this analysis.
            </p>
            
            <table>
                <thead>
                    <tr>
                        <th>Group</th>
                        <th style="text-align: center;">Students</th>
                        <th style="text-align: center;">Vision</th>
                        <th style="text-align: center;">Effort</th>
                        <th style="text-align: center;">Systems</th>
                        <th style="text-align: center;">Practice</th>
                        <th style="text-align: center;">Attitude</th>
                        <th style="text-align: center;">Overall</th>
                        <th style="text-align: center;">ERI</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                    
                    <tr style="background: linear-gradient(135deg, #667eea, #764ba2); color: white;">
                        <td style="padding: 16px; font-weight: bold;">SCHOOL AVERAGE</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{school_stats['n_students']}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{school_stats['vision']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{school_stats['effort']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{school_stats['systems']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{school_stats['practice']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{school_stats['attitude']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold; font-size: 1.1em;">{school_stats['overall']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold; font-size: 1.1em;">{school_stats['eri']:.2f}</td>
                    </tr>
                </tbody>
            </table>
            
            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <p><strong>Note:</strong> Groups with fewer than 5 students are excluded from this table but included in school-wide statistics.</p>
            </div>
        </div>
"""
    return html

def generate_distributions_section(df, org_name):
    """Generate score distribution charts section"""
    html = """
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                SCORE DISTRIBUTIONS
            </h1>
        </div>
        
        <div class="section">
            <h2>📈 Score Distribution Analysis</h2>
            <p>Distribution of VESPA scores for Cycle 1 baseline. Bar charts show school percentages, red lines show national distribution.</p>
"""
    
    col_map = {'Vision': 'vScale', 'Effort': 'eScale', 'Systems': 'sScale', 
               'Practice': 'pScale', 'Attitude': 'aScale', 'Overall': 'oScale'}
    
    for dim, col in col_map.items():
        chart = create_score_distribution_chart(df, dim, COLORS[dim], col)
        if chart:
            chart_html = pio.to_html(chart, full_html=False, include_plotlyjs=False, div_id=f'dist-{dim.lower()}')
            html += f"""
            <div class="chart-container">
                <div class="responsive-chart">
                    {chart_html}
                </div>
            </div>
"""
    
    html += """
        </div>
"""
    return html

def generate_recommendations_section(stats, insights, strongest_dim, weakest_dim, school_name):
    """Generate actionable recommendations section - easily editable"""
    
    # Sort insights to find areas needing attention
    insights_sorted = sorted(insights, key=lambda x: x['percentage'])
    lowest_insight = insights_sorted[0]
    highest_insight = insights_sorted[-1]
    
    # Determine ERI status
    eri = stats['eri']
    if eri >= 4.0:
        eri_action = "Continue to maintain high levels of exam readiness through regular check-ins and celebration of student confidence."
    elif eri >= 3.5:
        eri_action = "Build on solid foundation by implementing targeted exam preparation workshops and peer mentoring programs."
    elif eri >= 3.0:
        eri_action = "Implement structured exam preparation program including study skills workshops, mock exam practice, and one-to-one support for students scoring below 3."
    else:
        eri_action = "Priority focus area - establish comprehensive exam readiness program with dedicated resources, regular progress monitoring, and pastoral support."
    
    # VESPA activities based on weakest dimension
    vespa_activities = {
        'vision': [
            "Career planning workshops with guest speakers from various professions",
            "Goal-setting sessions at the start of each half term",
            "University and apprenticeship visits to broaden horizons",
            "Personal development planning tutorials",
            "Alumni talks to inspire and provide role models"
        ],
        'effort': [
            "Time management and productivity workshops",
            "Study habits tracking and reflection exercises",
            "Peer accountability partnerships",
            "Recognition and rewards for sustained effort",
            "Independent study planning sessions"
        ],
        'systems': [
            "Organization and filing systems workshop",
            "Digital and physical planner training",
            "Note-taking techniques masterclass",
            "Deadline management and calendar skills",
            "Study space organization guidance"
        ],
        'practice': [
            "Active recall and retrieval practice training",
            "Spaced repetition techniques workshop",
            "Self-testing strategies and resources",
            "Interleaving practice guidance",
            "Exam technique and timed practice sessions"
        ],
        'attitude': [
            "Growth mindset development workshops",
            "Resilience and stress management sessions",
            "Confidence-building activities",
            "Positive psychology interventions",
            "Peer support and mentoring programs"
        ]
    }
    
    # Get activities for weakest dimension
    suggested_activities = vespa_activities.get(weakest_dim, vespa_activities['systems'])
    activities_html = "".join([f"<li>{activity}</li>" for activity in suggested_activities])
    
    # Generate insight-based recommendations
    insight_recommendations = ""
    for insight in insights_sorted[:3]:  # Bottom 3 insights
        if insight['percentage'] < 60:
            insight_recommendations += f"""
                <li><strong>{insight['icon']} {insight['title']}</strong> ({insight['percentage']:.1f}% agreement) - 
                Implement targeted interventions such as group workshops, peer mentoring, or one-to-one coaching sessions.</li>
"""
    
    if not insight_recommendations:
        insight_recommendations = "<li>All psychometric insights show strong performance (60%+). Continue current practices and monitor in Cycle 2.</li>"
    
    html = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                RECOMMENDATIONS & ACTION PLAN
            </h1>
        </div>
        
        <div class="section" contenteditable="true" style="border: 2px dashed transparent; transition: border 0.3s;" 
             onmouseover="this.style.borderColor='#667eea'" onmouseout="this.style.borderColor='transparent'">
            <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1)); padding: 15px; border-radius: 8px; margin-bottom: 25px;">
                <p style="margin: 0; color: #667eea; font-weight: 600;">💡 This section is editable - Click anywhere to customize recommendations for your school</p>
            </div>
            
            <h2>🎯 Strategic Recommendations for {school_name}</h2>
            
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">1. Build on Strengths</h3>
                <div style="background: rgba(16, 185, 129, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #10b981;">
                    <p><strong>Leverage {strongest_dim.title()} Performance ({stats[strongest_dim]:.2f})</strong></p>
                    <ul style="margin-top: 10px; line-height: 1.8;">
                        <li>Share best practices from high-performing groups with the wider school community</li>
                        <li>Celebrate and recognize students demonstrating excellence in {strongest_dim.title()}</li>
                        <li>Use {strongest_dim.title()} success as foundation for developing other VESPA dimensions</li>
                        <li>Document successful strategies for replication in Cycle 2</li>
                    </ul>
                </div>
            </div>
            
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">2. Target Development Areas</h3>
                <div style="background: rgba(245, 158, 11, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <p><strong>Focus on {weakest_dim.title()} ({stats[weakest_dim]:.2f})</strong></p>
                    <ul style="margin-top: 10px; line-height: 1.8;">
                        <li>Conduct staff training on evidence-based {weakest_dim.title()} development strategies</li>
                        <li>Integrate {weakest_dim.title()}-building activities into weekly tutorial program</li>
                        <li>Monitor progress through regular student surveys and check-ins</li>
                        <li>Provide targeted resources and intervention for students scoring below 3</li>
                    </ul>
                </div>
            </div>
            
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">3. Enhance Exam Readiness (ERI: {stats['eri']:.2f})</h3>
                <div style="background: rgba(251, 191, 36, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #fbbf24;">
                    <p><strong>Action Required:</strong> {eri_action}</p>
                    <ul style="margin-top: 10px; line-height: 1.8;">
                        <li>Run dedicated exam preparation workshops focusing on study techniques and time management</li>
                        <li>Establish peer support groups for exam preparation</li>
                        <li>Provide regular mock exams with detailed feedback</li>
                        <li>Offer one-to-one support for students expressing low confidence</li>
                        <li>Communicate clearly about available support services</li>
                    </ul>
                </div>
            </div>
            
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">4. Address Questionnaire Insight Priorities</h3>
                <div style="background: rgba(139, 92, 246, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #8b5cf6;">
                    <p><strong>Focus Areas Based on Psychometric Analysis:</strong></p>
                    <ul style="margin-top: 10px; line-height: 1.8;">
                        {insight_recommendations}
                        <li>Review Cycle 2 results to measure impact of interventions</li>
                    </ul>
                </div>
            </div>
            
            <div style="margin: 30px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">📚 Suggested VESPA Activities</h3>
                <div style="background: linear-gradient(to right, #f8f9fa, #ffffff); padding: 25px; border-radius: 10px; border: 2px solid #667eea;">
                    <p style="margin-bottom: 15px;"><strong>Priority Focus: {weakest_dim.title()} Development</strong></p>
                    <p style="margin-bottom: 15px; color: #666;">
                        The following evidence-based activities are recommended to strengthen {weakest_dim.title()} skills.
                        These can be integrated into tutorial time, assemblies, or dedicated intervention sessions.
                    </p>
                    <ul style="line-height: 2; margin-top: 15px;">
                        {activities_html}
                    </ul>
                    
                    <div style="margin-top: 25px; padding: 20px; background: rgba(102, 126, 234, 0.08); border-radius: 8px;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Additional Universal Activities</h4>
                        <ul style="line-height: 1.8;">
                            <li><strong>Weekly VESPA Check-ins:</strong> 5-minute tutorial discussions on one VESPA dimension per week</li>
                            <li><strong>Student Success Stories:</strong> Share examples of students demonstrating strong VESPA characteristics</li>
                            <li><strong>VESPA Champions:</strong> Appoint student ambassadors to promote positive mindsets and study habits</li>
                            <li><strong>Parent Communication:</strong> Share VESPA framework with families to support home learning</li>
                            <li><strong>Staff CPD:</strong> Regular training on embedding VESPA principles across the curriculum</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; margin-bottom: 15px;">5. Monitor and Evaluate</h3>
                <div style="background: rgba(59, 130, 246, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <p><strong>Tracking Progress Through Cycle 2 and 3:</strong></p>
                    <ul style="margin-top: 10px; line-height: 1.8;">
                        <li>Schedule Cycle 2 assessment for January 2026 to measure mid-year progress</li>
                        <li>Identify students showing limited improvement for early intervention</li>
                        <li>Celebrate and share success stories of students showing significant growth</li>
                        <li>Adjust intervention strategies based on Cycle 2 data</li>
                        <li>Plan for Cycle 3 (end of year) to measure overall annual development</li>
                        <li>Use data to inform next year's baseline targets and support strategies</li>
                    </ul>
                </div>
            </div>
            
            <div style="margin: 30px 0; padding: 25px; background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05)); border-radius: 10px; border: 1px solid #667eea;">
                <h4 style="color: #2c3e50; margin-bottom: 15px;">💭 Space for Your Notes and Additional Recommendations</h4>
                <div style="min-height: 150px; padding: 15px; background: white; border-radius: 5px; border: 1px dashed #ccc;">
                    <p style="color: #999; font-style: italic;">
                        Click here to add your school-specific observations, additional recommendations, or action plans...
                    </p>
                    <br><br><br><br>
                </div>
            </div>
        </div>
"""
    return html

def generate_footer(org_name):
    """Generate report footer"""
    return f"""
        <div class="footer">
            <p>© 2025 VESPA Education Analytics | {org_name} - Confidential Report</p>
            <p style="margin-top: 10px; font-size: 0.9em;">Cycle 1 Baseline | Academic Year 2025/26</p>
        </div>
"""

def main():
    """Main execution function"""
    csv_path = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\DASHBOARD-Vue\EACT - Cycle 1.csv"
    
    try:
        # Load data
        df = load_data(csv_path)
        
        # Generate Executive Summary
        exec_filename = generate_executive_summary(df)
        
        # Generate individual school reports
        schools = [
            'Montpelier High School',
            'Ousedale School',
            'Daventry 6th Form',
            'West Walsall Academy',
            'Crest Academy',
            'North Birmingham Academy'
        ]
        
        school_files = []
        for school in schools:
            school_df = df[df['VESPA Customer'] == school]
            if len(school_df) > 0:
                filename = generate_individual_school_report(school, school_df, df)
                school_files.append(filename)
        
        print(f"\n{'='*80}")
        print("🎉 ALL REPORTS GENERATED SUCCESSFULLY!")
        print(f"{'='*80}")
        print(f"\nExecutive Summary: {exec_filename}")
        print(f"\nIndividual School Reports:")
        for f in school_files:
            print(f"  - {f}")
        print(f"\n{'='*80}\n")
        
        return exec_filename, school_files
        
    except Exception as e:
        print(f"\n❌ Error generating reports: {e}")
        import traceback
        traceback.print_exc()
        return None, []

if __name__ == '__main__':
    main()

