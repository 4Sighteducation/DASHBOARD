#!/usr/bin/env python3
"""
Generate Hartpury University Cycle 1 Baseline VESPA Report
Complete HTML report with Gender and Residential analysis sections
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from datetime import datetime
from scipy import stats as scipy_stats

# National averages for comparison
NATIONAL_AVERAGES = {
    'Vision': 6.1,
    'Effort': 5.49,
    'Systems': 5.27,
    'Practice': 5.75,
    'Attitude': 5.59,
    'Overall': 5.64
}

# National distributions (approximated from Demo report)
NATIONAL_DISTRIBUTIONS = {
    'Vision': {1: 1.65, 2: 4.63, 3: 10.98, 4: 8.29, 5: 10.50, 6: 21.72, 7: 10.58, 8: 16.81, 9: 6.33, 10: 8.50},
    'Effort': {1: 5.51, 2: 3.75, 3: 15.47, 4: 11.72, 5: 13.32, 6: 14.87, 7: 12.60, 8: 8.88, 9: 11.00, 10: 2.89},
    'Systems': {1: 5.94, 2: 6.73, 3: 11.79, 4: 17.16, 5: 9.29, 6: 19.20, 7: 9.10, 8: 13.03, 9: 4.11, 10: 3.65},
    'Practice': {1: 3.55, 2: 4.61, 3: 8.95, 4: 13.63, 5: 18.24, 6: 10.03, 7: 16.30, 8: 11.81, 9: 7.73, 10: 5.16},
    'Attitude': {1: 3.77, 2: 6.76, 3: 11.72, 4: 10.00, 5: 12.01, 6: 20.62, 7: 11.84, 8: 13.23, 9: 6.69, 10: 3.36},
    'Overall': {1: 0.74, 2: 2.60, 3: 8.48, 4: 14.87, 5: 20.08, 6: 21.72, 7: 16.11, 8: 10.20, 9: 3.92, 10: 1.27}
}

COLORS = {
    'Vision': '#e59437',
    'Effort': '#86b4f0',
    'Systems': '#72cb44',
    'Practice': '#7f31a4',
    'Attitude': '#f032e6',
    'Overall': '#ffd700'
}

# Statement to category mapping
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
    "I know what grades I want to achieve": 'Vision'
}

def load_data(csv_path):
    """Load and clean Cycle 1 data"""
    print("Loading Hartpury data...")
    df = pd.read_csv(csv_path)
    
    # Filter for Cycle 1 only
    df_cycle1 = df[df['Cycle'] == 1.0].copy()
    
    # Keep only rows with valid VESPA scores
    vespa_cols = ['vScale', 'eScale', 'sScale', 'pScale', 'aScale', 'oScale']
    df_cycle1 = df_cycle1[df_cycle1[vespa_cols].notna().all(axis=1)]
    
    # Clean gender data
    df_cycle1['Gender'] = df_cycle1['Gender'].replace({'12': 'Prefer not to say'})
    
    print(f"✅ Loaded {len(df_cycle1)} students with complete Cycle 1 VESPA data")
    print(f"   Faculties: {df_cycle1['Faculty'].nunique()}")
    print(f"   Mean Overall: {df_cycle1['oScale'].mean():.2f}")
    
    return df_cycle1

def calculate_distribution(series):
    """Calculate percentage distribution for scores 1-10"""
    total = len(series)
    distribution = {}
    for score in range(1, 11):
        count = (series.round() == score).sum()
        distribution[score] = (count / total * 100) if total > 0 else 0
    return distribution

def create_score_distribution_chart(df, dimension, color, col_name):
    """Create distribution chart comparing college to national"""
    values = df[col_name].dropna()
    dist = calculate_distribution(values)
    
    college_pct = [dist[i] for i in range(1, 11)]
    national_pct = [NATIONAL_DISTRIBUTIONS[dimension][i] for i in range(1, 11)]
    
    fig = go.Figure()
    
    # College bars
    fig.add_trace(go.Bar(
        x=list(range(1, 11)),
        y=college_pct,
        name='Hartpury',
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
        text=f"Hartpury: {college_mean:.1f}<br>National: {national_mean}",
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

def create_faculty_comparison_chart(faculty_stats):
    """Create faculty comparison bar chart"""
    faculties = [f['faculty'] for f in faculty_stats]
    
    fig = go.Figure()
    
    dimensions = [('vision', 'Vision'), ('effort', 'Effort'), ('systems', 'Systems'), 
                  ('practice', 'Practice'), ('attitude', 'Attitude')]
    
    for dim_key, dim_name in dimensions:
        fig.add_trace(go.Bar(
            name=dim_name,
            x=faculties,
            y=[f[dim_key] for f in faculty_stats],
            marker_color=COLORS[dim_name]
        ))
    
    fig.update_layout(
        title='Faculty VESPA Performance Comparison - Cycle 1 Baseline',
        xaxis_title='Faculty',
        yaxis=dict(title='Mean Score', range=[0, 10]),
        barmode='group',
        height=500,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        paper_bgcolor='white',
        plot_bgcolor='rgba(240,240,240,0.3)'
    )
    
    return fig

def create_comparison_chart(stats_list, x_labels, title, x_title):
    """Generic comparison chart for gender/residential"""
    fig = go.Figure()
    
    dimensions = [('vision', 'Vision'), ('effort', 'Effort'), ('systems', 'Systems'), 
                  ('practice', 'Practice'), ('attitude', 'Attitude'), ('overall', 'Overall')]
    
    for dim_key, dim_name in dimensions:
        values = [s[dim_key] for s in stats_list]
        fig.add_trace(go.Bar(
            name=dim_name,
            x=x_labels,
            y=values,
            marker_color=COLORS[dim_name],
            text=[f"{v:.2f}" for v in values],
            textposition='auto'
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis=dict(title='Mean Score', range=[0, 8]),
        barmode='group',
        height=400,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        paper_bgcolor='white',
        plot_bgcolor='rgba(240,240,240,0.3)'
    )
    
    return fig

def generate_html_report(df):
    """Generate complete HTML report"""
    print("\n" + "="*80)
    print("GENERATING HARTPURY UNIVERSITY CYCLE 1 BASELINE REPORT")
    print("="*80)
    
    # Calculate overall statistics
    overall_stats = {
        'n_students': len(df),
        'n_faculties': df['Faculty'].nunique(),
        'vision': df['vScale'].mean(),
        'effort': df['eScale'].mean(),
        'systems': df['sScale'].mean(),
        'practice': df['pScale'].mean(),
        'attitude': df['aScale'].mean(),
        'overall': df['oScale'].mean()
    }
    
    print(f"\nOverall: {overall_stats['n_students']} students, {overall_stats['n_faculties']} faculties")
    print(f"Mean scores - V:{overall_stats['vision']:.2f} E:{overall_stats['effort']:.2f} S:{overall_stats['systems']:.2f} P:{overall_stats['practice']:.2f} A:{overall_stats['attitude']:.2f} O:{overall_stats['overall']:.2f}")
    
    # Faculty statistics
    print("\nCalculating faculty statistics...")
    faculty_stats = []
    for faculty in df['Faculty'].dropna().unique():
        faculty_df = df[df['Faculty'] == faculty]
        n = len(faculty_df)
        if n < 5:
            continue
        
        faculty_stats.append({
            'faculty': faculty,
            'n': n,
            'vision': faculty_df['vScale'].mean(),
            'effort': faculty_df['eScale'].mean(),
            'systems': faculty_df['sScale'].mean(),
            'practice': faculty_df['pScale'].mean(),
            'attitude': faculty_df['aScale'].mean(),
            'overall': faculty_df['oScale'].mean()
        })
    
    faculty_stats = sorted(faculty_stats, key=lambda x: x['overall'], reverse=True)
    print(f"   {len(faculty_stats)} faculties analyzed")
    
    # Gender statistics
    print("\nCalculating gender statistics...")
    gender_stats = []
    for gender in ['Male', 'Female']:
        gender_df = df[df['Gender'] == gender]
        if len(gender_df) > 0:
            gender_stats.append({
                'gender': gender,
                'n': len(gender_df),
                'vision': gender_df['vScale'].mean(),
                'effort': gender_df['eScale'].mean(),
                'systems': gender_df['sScale'].mean(),
                'practice': gender_df['pScale'].mean(),
                'attitude': gender_df['aScale'].mean(),
                'overall': gender_df['oScale'].mean()
            })
    print(f"   Male: {gender_stats[0]['n']} students (Overall: {gender_stats[0]['overall']:.2f})")
    print(f"   Female: {gender_stats[1]['n']} students (Overall: {gender_stats[1]['overall']:.2f})")
    
    # Residential statistics
    print("\nCalculating residential statistics...")
    residential_stats = []
    for status in ['Yes', 'No']:
        res_df = df[df['Residential'] == status]
        if len(res_df) > 0:
            residential_stats.append({
                'status': 'Residential' if status == 'Yes' else 'Non-Residential',
                'status_code': status,
                'n': len(res_df),
                'vision': res_df['vScale'].mean(),
                'effort': res_df['eScale'].mean(),
                'systems': res_df['sScale'].mean(),
                'practice': res_df['pScale'].mean(),
                'attitude': res_df['aScale'].mean(),
                'overall': res_df['oScale'].mean()
            })
    print(f"   Residential: {residential_stats[0]['n']} students (Overall: {residential_stats[0]['overall']:.2f})")
    print(f"   Non-Residential: {residential_stats[1]['n']} students (Overall: {residential_stats[1]['overall']:.2f})")
    
    # Statement analysis
    print("\nAnalyzing statements...")
    statement_cols = [col for col in df.columns if col in STATEMENT_MAPPING]
    statement_analysis = []
    
    for statement in statement_cols:
        values = df[statement].dropna()
        if len(values) > 0:
            mean_val = values.mean()
            std_val = values.std()
            variance_val = std_val ** 2 if not pd.isna(std_val) else 0
            
            statement_analysis.append({
                'statement': statement,
                'category': STATEMENT_MAPPING.get(statement, 'Unknown'),
                'mean': mean_val,
                'std': std_val,
                'variance': variance_val,
                'n': len(values)
            })
    
    statement_analysis = sorted(statement_analysis, key=lambda x: x['mean'], reverse=True)
    print(f"   {len(statement_analysis)} statements analyzed")
    print(f"   Highest: {statement_analysis[0]['statement'][:50]}... ({statement_analysis[0]['mean']:.2f}, var={statement_analysis[0]['variance']:.2f})")
    print(f"   Lowest: {statement_analysis[-1]['statement'][:50]}... ({statement_analysis[-1]['mean']:.2f}, var={statement_analysis[-1]['variance']:.2f})")
    
    # Gender statement differences
    print("\nCalculating gender statement differences...")
    gender_stmt_diffs = []
    for statement in statement_cols:
        male_mean = df[df['Gender'] == 'Male'][statement].mean()
        female_mean = df[df['Gender'] == 'Female'][statement].mean()
        if not pd.isna(male_mean) and not pd.isna(female_mean):
            gender_stmt_diffs.append({
                'statement': statement,
                'category': STATEMENT_MAPPING.get(statement, 'Unknown'),
                'male': male_mean,
                'female': female_mean,
                'difference': abs(male_mean - female_mean),
                'higher': 'Male' if male_mean > female_mean else 'Female'
            })
    
    gender_stmt_diffs = sorted(gender_stmt_diffs, key=lambda x: x['difference'], reverse=True)
    print(f"   Top difference: {gender_stmt_diffs[0]['statement'][:50]}... ({gender_stmt_diffs[0]['difference']:.2f})")
    
    # Residential statement differences
    print("\nCalculating residential statement differences...")
    residential_stmt_diffs = []
    for statement in statement_cols:
        res_mean = df[df['Residential'] == 'Yes'][statement].mean()
        nonres_mean = df[df['Residential'] == 'No'][statement].mean()
        if not pd.isna(res_mean) and not pd.isna(nonres_mean):
            residential_stmt_diffs.append({
                'statement': statement,
                'category': STATEMENT_MAPPING.get(statement, 'Unknown'),
                'residential': res_mean,
                'non_residential': nonres_mean,
                'difference': abs(res_mean - nonres_mean),
                'higher': 'Residential' if res_mean > nonres_mean else 'Non-Residential'
            })
    
    residential_stmt_diffs = sorted(residential_stmt_diffs, key=lambda x: x['difference'], reverse=True)
    print(f"   Top difference: {residential_stmt_diffs[0]['statement'][:50]}... ({residential_stmt_diffs[0]['difference']:.2f})")
    
    # Year Group statistics - combine Year 1 + Year 12, and Year 2 + Year 13
    print("\nCalculating year group statistics...")
    
    # Create a normalized year group column
    df['Year_Group_Normalized'] = df['Year Gp'].apply(lambda x: 
        '1' if x in [1, '1', 12, '12'] else 
        '2' if x in [2, '2', 13, '13'] else 
        str(x) if pd.notna(x) else None
    )
    
    year_group_stats = []
    year_groups_unique = df['Year_Group_Normalized'].dropna().unique()
    
    for year_group in sorted(year_groups_unique, key=lambda x: int(x) if str(x).isdigit() else 99):
        yg_df = df[df['Year_Group_Normalized'] == year_group]
        if len(yg_df) >= 10:  # Only include year groups with at least 10 students
            year_group_stats.append({
                'year_group': str(year_group),
                'n': len(yg_df),
                'vision': yg_df['vScale'].mean(),
                'effort': yg_df['eScale'].mean(),
                'systems': yg_df['sScale'].mean(),
                'practice': yg_df['pScale'].mean(),
                'attitude': yg_df['aScale'].mean(),
                'overall': yg_df['oScale'].mean()
            })
    
    year_group_stats = sorted(year_group_stats, key=lambda x: x['overall'], reverse=True)
    print(f"   {len(year_group_stats)} year groups analyzed (Year 1 combines Year 1+12, Year 2 combines Year 2+13)")
    
    # Create visualizations
    print("\nCreating visualizations...")
    
    # Distribution charts
    print("   - Distribution charts...")
    dist_charts = {}
    col_map = {'Vision': 'vScale', 'Effort': 'eScale', 'Systems': 'sScale', 
               'Practice': 'pScale', 'Attitude': 'aScale', 'Overall': 'oScale'}
    
    for dim, col in col_map.items():
        dist_charts[dim] = create_score_distribution_chart(df, dim, COLORS[dim], col)
    
    # Faculty chart
    print("   - Faculty comparison chart...")
    faculty_chart = create_faculty_comparison_chart(faculty_stats)
    
    # Gender chart
    print("   - Gender comparison chart...")
    gender_chart = create_comparison_chart(
        gender_stats,
        [g['gender'] for g in gender_stats],
        'VESPA Scores by Gender - Cycle 1',
        'Gender'
    )
    
    # Residential chart
    print("   - Residential comparison chart...")
    residential_chart = create_comparison_chart(
        residential_stats,
        [r['status'] for r in residential_stats],
        'VESPA Scores by Residential Status - Cycle 1',
        'Residential Status'
    )
    
    # Year Group chart
    print("   - Year group comparison chart...")
    year_group_chart = None
    if len(year_group_stats) > 0:
        year_group_chart = create_comparison_chart(
            year_group_stats,
            [yg['year_group'] for yg in year_group_stats],
            'VESPA Scores by Year Group - Cycle 1',
            'Year Group'
        )
    
    # Generate HTML
    print("\nGenerating HTML content...")
    html = build_html(
        overall_stats,
        faculty_stats,
        gender_stats,
        residential_stats,
        year_group_stats,
        statement_analysis,
        gender_stmt_diffs,
        residential_stmt_diffs,
        dist_charts,
        faculty_chart,
        gender_chart,
        residential_chart,
        year_group_chart
    )
    
    # Write file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Hartpury_Cycle1_Baseline_{timestamp}.html"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n{'='*80}")
    print(f"✅ REPORT GENERATED SUCCESSFULLY")
    print(f"{'='*80}")
    print(f"Filename: {filename}")
    print(f"Location: {Path.cwd()}")
    print(f"{'='*80}\n")
    
    return filename

def build_html(overall, faculties, gender, residential, year_groups, statements, 
               gender_diffs, residential_diffs, dist_charts, 
               faculty_chart, gender_chart, residential_chart, year_group_chart):
    """Build the complete HTML document"""
    
    # Convert charts to HTML divs
    dist_html = {}
    for dim, chart in dist_charts.items():
        dist_html[dim] = pio.to_html(chart, full_html=False, include_plotlyjs=False, div_id=f'dist-{dim.lower()}')
    
    faculty_html = pio.to_html(faculty_chart, full_html=False, include_plotlyjs=False, div_id='faculty-chart')
    gender_html = pio.to_html(gender_chart, full_html=False, include_plotlyjs=False, div_id='gender-chart')
    residential_html = pio.to_html(residential_chart, full_html=False, include_plotlyjs=False, div_id='residential-chart')
    year_group_html = pio.to_html(year_group_chart, full_html=False, include_plotlyjs=False, div_id='year-group-chart') if year_group_chart else ""
    
    report_date = datetime.now().strftime("%B %d, %Y")
    
    # Determine performance vs national
    def vs_national(score, nat_score):
        diff = score - nat_score
        if diff > 0.2:
            return f'↑ {score:.2f}', 'positive', diff
        elif diff < -0.2:
            return f'↓ {score:.2f}', 'negative', diff
        else:
            return f'• {score:.2f}', 'neutral', diff
    
    # Generate insights
    dims = ['vision', 'effort', 'systems', 'practice', 'attitude']
    dim_scores = {d: overall[d] for d in dims}
    strongest_dim = max(dim_scores, key=dim_scores.get)
    weakest_dim = min(dim_scores, key=dim_scores.get)
    
    # Gender insights
    gender_diff = abs(gender[0]['overall'] - gender[1]['overall']) if len(gender) >= 2 else 0
    higher_gender = gender[0] if len(gender) >= 2 and gender[0]['overall'] > gender[1]['overall'] else gender[1] if len(gender) >= 2 else None
    
    # Residential insights
    res_diff = abs(residential[0]['overall'] - residential[1]['overall']) if len(residential) >= 2 else 0
    higher_res = residential[0] if len(residential) >= 2 and residential[0]['overall'] > residential[1]['overall'] else residential[1] if len(residential) >= 2 else None
    
    # Build HTML (this will be very long, so I'll create it in a structured way)
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hartpury University - VESPA Cycle 1 Baseline Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        {get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        {generate_header(report_date)}
        {generate_executive_summary(overall, faculties, gender, residential, statements, strongest_dim, weakest_dim, higher_gender, higher_res, gender_diff, res_diff)}
        {generate_baseline_overview(overall)}
        {generate_distribution_section(dist_html)}
        {generate_faculty_section(faculties, faculty_html, overall)}
        {generate_gender_section(gender, gender_diffs, gender_html)}
        {generate_residential_section(residential, residential_diffs, residential_html)}
        {generate_year_group_section(year_groups, year_group_html)}
        {generate_statement_section(statements)}
        {generate_footer()}
    </div>
</body>
</html>
"""
    
    return html

def get_css_styles():
    """Return CSS styles for the report"""
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
            background: linear-gradient(135deg, #dc143c 0%, #8b0000 100%);
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
            color: #dc143c;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .section h3 {
            color: #8b0000;
            margin: 20px 0 10px 0;
            font-size: 1.4em;
        }
        
        .key-insights {
            background: #f8f9fa;
            border-left: 4px solid #dc143c;
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
            background: linear-gradient(135deg, #dc143c 0%, #8b0000 100%);
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
            background: #dc143c;
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
        
        @media print {
            @page {
                size: A4;
                margin: 12mm 8mm;
            }
            
            body {
                background: white !important;
                margin: 0;
                padding: 0;
                width: 100%;
            }
            
            .container {
                max-width: 100%;
                width: 190mm;
                margin: 0 auto;
                padding: 0;
                box-shadow: none;
            }
            
            .report-header {
                padding: 15px !important;
                margin-bottom: 5px !important;
            }
            
            .report-header img {
                height: 60px !important;
            }
            
            .report-header h1 {
                font-size: 1.4em !important;
                margin-bottom: 5px !important;
            }
            
            .report-header h2 {
                font-size: 1.2em !important;
            }
            
            .report-header button {
                display: none !important;
            }
            
            .executive-summary, .section {
                padding: 12px !important;
                margin-bottom: 8px !important;
            }
            
            .section {
                page-break-inside: avoid;
            }
            
            /* Hide faculty cards in print, show only table */
            .faculty-cards-grid {
                display: none !important;
            }
            
            /* Also hide the key insights grids in executive summary for more compact print */
            .key-insights div[style*="grid-template-columns"] {
                font-size: 0.75em !important;
            }
            
            .key-insights div[style*="grid-template-columns"] > div {
                padding: 8px !important;
            }
            
            .chart-container {
                page-break-inside: avoid;
                margin: 3px 0 !important;
                padding: 3px !important;
                width: 100%;
                max-height: 65mm;
                overflow: hidden;
            }
            
            .responsive-chart {
                page-break-inside: avoid;
                width: 100% !important;
                max-width: 190mm !important;
                height: 60mm !important;
                max-height: 60mm !important;
                overflow: hidden !important;
            }
            
            .responsive-chart > div {
                width: 380mm !important;
                height: 120mm !important;
                transform: scale(0.5) !important;
                transform-origin: top left !important;
            }
            
            .js-plotly-plot {
                width: 100% !important;
                height: 100% !important;
            }
            
            .modebar {
                display: none !important;
            }
            
            table {
                page-break-inside: avoid;
                font-size: 0.65em;
            }
            
            th, td {
                padding: 4px 3px !important;
            }
            
            h1 {
                font-size: 1.4em !important;
                margin-bottom: 8px !important;
            }
            
            h2 {
                font-size: 1.2em !important;
                margin-bottom: 8px !important;
            }
            
            h3 {
                font-size: 1.0em !important;
                margin: 10px 0 5px 0 !important;
            }
            
            h4 {
                font-size: 0.9em !important;
            }
            
            p, li {
                font-size: 0.75em !important;
                line-height: 1.3 !important;
            }
            
            .stats-grid {
                grid-template-columns: repeat(3, 1fr) !important;
                gap: 5px !important;
                font-size: 0.7em !important;
            }
            
            .stat-card {
                padding: 8px 5px !important;
            }
            
            .stat-card h4 {
                font-size: 0.7em !important;
            }
            
            .stat-card .value {
                font-size: 1.2em !important;
            }
            
            .stat-card small {
                font-size: 0.65em !important;
            }
            
            .key-insights {
                padding: 10px !important;
                margin: 8px 0 !important;
            }
            
            .key-insights > div {
                padding: 10px !important;
            }
            
            /* Section dividers more compact */
            div[style*="background: #f0f4f8"] {
                padding: 10px 0 !important;
                margin-top: 15px !important;
            }
            
            div[style*="background: #f0f4f8"] h1 {
                font-size: 1.3em !important;
                padding-bottom: 5px !important;
            }
        }
"""

def generate_header(report_date):
    """Generate report header"""
    return f"""
        <div class="report-header">
            <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 20px;">
                <img src="https://i0.wp.com/northernhive.com/wp-content/uploads/2020/07/HARTPURY-UNIVERSITY-REV-ON-RED.jpg?fit=1457%2C963&ssl=1" 
                     alt="Hartpury University Logo" 
                     style="height: 100px; object-fit: contain; max-width: 400px;">
            </div>
            <h1 style="color: #dc143c; margin-bottom: 10px; text-align: center;">Hartpury University</h1>
            <h2 style="color: #8b0000; text-align: center;">VESPA Cycle 1 Baseline Report</h2>
            <p class="report-date" style="text-align: center;">Generated: {report_date}</p>
            
            <div style="margin-top: 20px; text-align: center;">
                <button onclick="window.print();" style="
                    background: linear-gradient(135deg, #dc143c, #8b0000);
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    font-size: 1em;
                    font-weight: 600;
                    border-radius: 25px;
                    cursor: pointer;
                    box-shadow: 0 4px 15px rgba(220, 20, 60, 0.3);
                    transition: all 0.3s;
                " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(220, 20, 60, 0.4)';" 
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(220, 20, 60, 0.3)';">
                    Download as PDF
                </button>
            </div>
        </div>
"""

def generate_executive_summary(overall, faculties, gender, residential, statements, 
                               strongest_dim, weakest_dim, higher_gender, higher_res, 
                               gender_diff, res_diff):
    """Generate executive summary section"""
    
    # Calculate performance vs national
    overall_vs_nat = overall['overall'] - NATIONAL_AVERAGES['Overall']
    overall_status = "above" if overall_vs_nat > 0.1 else "in line with" if overall_vs_nat > -0.1 else "below"
    
    top_faculty = faculties[0]
    
    html = f"""
        <div class="executive-summary">
            <h2>Executive Summary</h2>
            <p>This comprehensive VESPA Cycle 1 baseline analysis for Hartpury University examines student mindset and study skills 
            across <strong>{overall['n_students']:,} students</strong> in <strong>{overall['n_faculties']} faculties</strong>. 
            This baseline assessment establishes the starting point for tracking student development throughout the 2024/25 academic year.</p>
            
            <p style="margin-top: 15px;"><strong>Overall Performance:</strong> Hartpury students score {overall_status} national 
            average ({overall['overall']:.2f} vs {NATIONAL_AVERAGES['Overall']}), demonstrating {"strong" if overall_vs_nat > 0 else "solid"} 
            engagement with learning mindsets and study skills at this baseline stage.</p>
            
            <p style="margin-top: 15px;"><strong>Looking Ahead:</strong> This Cycle 1 baseline will be compared against Cycle 2 
            (mid-year, January) and Cycle 3 (end-of-year). Typically, students experience a natural adjustment in Cycle 2 as 
            they engage with the realities of their courses, before showing strong growth and recovery by Cycle 3. 
            This report establishes the foundation for measuring that growth journey.</p>
            
            <div class="key-insights" style="margin-top: 25px;">
                <h3 style="color: #dc143c; margin-bottom: 20px;">Key Baseline Findings</h3>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px;">
                    <div style="background: rgba(220, 20, 60, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #dc143c;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Overall Baseline</h4>
                        <p>Students demonstrate {strongest_dim.title()} as their strongest dimension ({overall[strongest_dim]:.2f}), 
                        while {weakest_dim.title()} ({overall[weakest_dim]:.2f}) presents the primary development opportunity for the year ahead.</p>
                    </div>
                    
                    <div style="background: rgba(114, 203, 68, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #72cb44;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Faculty Snapshot</h4>
                        <p>{top_faculty['faculty']} leads with {top_faculty['overall']:.2f} overall score (n={top_faculty['n']} students). 
                        Significant variation across faculties indicates opportunities for peer learning and best practice sharing.</p>
                    </div>
                    
                    <div style="background: rgba(229, 148, 55, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #e59437;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Gender Insights</h4>
                        <p>{'Minimal' if gender_diff < 0.1 else 'Moderate' if gender_diff < 0.2 else 'Notable'} difference between genders 
                        (Male: {gender[0]['overall']:.2f}, Female: {gender[1]['overall']:.2f}). Both groups show strong baseline engagement.</p>
                    </div>
                    
                    <div style="background: rgba(134, 180, 240, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #86b4f0;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Residential Analysis</h4>
                        <p>{higher_res['status']} students score {'slightly' if res_diff < 0.2 else 'notably'} higher 
                        ({higher_res['overall']:.2f} vs {residential[1 if residential[0] == higher_res else 0]['overall']:.2f}), 
                        with {overall['n_students'] - higher_res['n']:,} non-residential and {higher_res['n']:,} residential students.</p>
                    </div>
                    
                    <div style="background: rgba(127, 49, 164, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #7f31a4;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Year Group Snapshot</h4>
                        <p>Analysis reveals performance variation across year groups, providing insights for cohort-specific interventions. 
                        Year group baseline profiles will be essential for tracking cohort development through Cycles 2 and 3.</p>
                    </div>
                    
                    <div style="background: rgba(240, 50, 230, 0.08); padding: 20px; border-radius: 8px; border-left: 4px solid #f032e6;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">Statement Insights</h4>
                        <p>Students score highest on goal-setting statements ("{statements[0]['statement'][:50]}..." at {statements[0]['mean']:.2f}) 
                        but struggle with practice strategies ("{statements[-1]['statement'][:50]}..." at {statements[-1]['mean']:.2f}). 
                        Variance analysis identifies where students need universal vs. differentiated support.</p>
                    </div>
                </div>
                
                <div style="margin-top: 25px; padding: 20px; background: linear-gradient(to right, rgba(220, 20, 60, 0.05), rgba(139, 0, 0, 0.05)); border-radius: 8px;">
                    <h4 style="color: #2c3e50; margin-bottom: 12px;">Strategic Priorities for 2024/25</h4>
                    <ul style="margin: 0; padding-left: 25px; line-height: 1.8;">
                        <li><strong>Build on Strengths:</strong> Leverage strong {strongest_dim.title()} baseline ({overall[strongest_dim]:.2f}) across all faculties</li>
                        <li><strong>Target Development:</strong> Focus interventions on {weakest_dim.title()} skills (current: {overall[weakest_dim]:.2f})</li>
                        <li><strong>Faculty Collaboration:</strong> Facilitate sharing of best practices from high-performing departments</li>
                        <li><strong>Monitor Progress:</strong> Track Cycle 2 (January) to identify early intervention needs and celebrate growth</li>
                        <li><strong>Targeted Support:</strong> Consider residential status and gender insights when designing support programs</li>
                    </ul>
                </div>
            </div>
        </div>
"""
    return html

def generate_baseline_overview(overall):
    """Generate baseline overview section with comparison to national"""
    
    def compare_to_nat(score, dim_name):
        nat = NATIONAL_AVERAGES[dim_name]
        diff = score - nat
        if diff > 0.2:
            status_color = '#28a745'
            arrow = '↑'
            status_text = 'Above National'
        elif diff < -0.2:
            status_color = '#dc3545'
            arrow = '↓'
            status_text = 'Below National'
        else:
            status_color = '#666'
            arrow = '•'
            status_text = 'On Par with National'
        
        return f"""
            <div class="stat-card">
                <h4>{dim_name}</h4>
                <div class="value">{score:.2f}</div>
                <small>National: {nat}</small>
                <div style="margin-top: 8px; font-size: 0.85em;">
                    <span style="color: white;">{arrow} {status_text}</span>
                </div>
            </div>
        """
    
    html = f"""
        <div class="section">
            <h2>📊 Cycle 1 Baseline Overview</h2>
            <p style="margin-bottom: 20px;">
                Baseline VESPA scores for {overall['n_students']:,} Hartpury University students compared to national averages.
                This establishes the starting point for measuring growth through Cycles 2 and 3.
            </p>
            
            <div class="stats-grid">
                {compare_to_nat(overall['vision'], 'Vision')}
                {compare_to_nat(overall['effort'], 'Effort')}
                {compare_to_nat(overall['systems'], 'Systems')}
                {compare_to_nat(overall['practice'], 'Practice')}
                {compare_to_nat(overall['attitude'], 'Attitude')}
                {compare_to_nat(overall['overall'], 'Overall')}
            </div>
        </div>
"""
    return html

def generate_distribution_section(dist_html):
    """Generate score distribution section"""
    html = """
        <div class="section">
            <h2>📈 Score Distribution Analysis</h2>
            <p>Distribution of VESPA scores for Cycle 1 baseline. Bar charts show Hartpury percentages, red lines show national distribution.</p>
"""
    
    for dim in ['Vision', 'Effort', 'Systems', 'Practice', 'Attitude', 'Overall']:
        html += f"""
            <div class="chart-container">
                <div class="responsive-chart">
                    {dist_html[dim]}
                </div>
            </div>
"""
    
    html += """
        </div>
"""
    return html

# This is getting very long - let me create the remaining functions
# I'll continue in the script...

def generate_faculty_section(faculties, faculty_html, overall):
    """Generate faculty comparison section"""
    
    # Determine performance relative to college average
    def faculty_indicator(faculty_score, overall_score):
        diff = faculty_score - overall_score
        if diff > 0.2:
            return '↑', '#28a745'
        elif diff < -0.2:
            return '↓', '#dc3545'
        else:
            return '•', '#666'
    
    # Generate faculty cards
    faculty_cards = ""
    for idx, fac in enumerate(faculties, 1):
        # Determine badge color
        if idx <= 3:
            badge_color = '#28a745'  # Green for top 3
        elif idx >= len(faculties) - 2:
            badge_color = '#dc3545'  # Red for bottom 3
        else:
            badge_color = '#dc143c'  # Hartpury red for middle
        
        border_color = badge_color
        
        faculty_cards += f"""
                <div style="background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border-top: 4px solid {border_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="color: #2c3e50; margin: 0; font-size: 1.1em; max-width: 70%;">{fac['faculty']}</h3>
                        <span style="background: {badge_color}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.9em; font-weight: 600;">#{idx}</span>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 15px;">
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(229,148,55,0.1), rgba(229,148,55,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #e59437; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Vision</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{fac['vision']:.2f}</div>
                        </div>
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(134,180,240,0.1), rgba(134,180,240,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #5690d6; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Effort</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{fac['effort']:.2f}</div>
                        </div>
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(114,203,68,0.1), rgba(114,203,68,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #72cb44; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Systems</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{fac['systems']:.2f}</div>
                        </div>
                        <div style="padding: 12px; background: linear-gradient(45deg, rgba(127,49,164,0.1), rgba(127,49,164,0.05)); border-radius: 8px; text-align: center;">
                            <div style="color: #7f31a4; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Practice</div>
                            <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{fac['practice']:.2f}</div>
                        </div>
                    </div>
                    
                    <div style="padding: 12px; background: linear-gradient(45deg, rgba(240,50,230,0.1), rgba(240,50,230,0.05)); border-radius: 8px; text-align: center; margin-bottom: 15px;">
                        <div style="color: #f032e6; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Attitude</div>
                        <div style="font-size: 1.8em; font-weight: bold; color: #2c3e50; margin-top: 5px;">{fac['attitude']:.2f}</div>
                    </div>
                    
                    <div style="padding: 15px; background: linear-gradient(135deg, #dc143c, #8b0000); border-radius: 10px; text-align: center; color: white;">
                        <div style="font-size: 0.9em; font-weight: 600; opacity: 0.9; text-transform: uppercase;">Overall Score</div>
                        <div style="font-size: 2.5em; font-weight: bold; margin: 5px 0;">{fac['overall']:.2f}</div>
                        <div style="font-size: 0.8em; opacity: 0.8;">n = {fac['n']} students</div>
                    </div>
                </div>
"""
    
    # Generate table rows
    table_rows = ""
    for fac in faculties:
        def indicator(score, nat):
            if score > nat + 0.2:
                return f'<span style="color: #28a745; font-weight: 600;">↑ {score:.2f}</span>'
            elif score < nat - 0.2:
                return f'<span style="color: #dc3545; font-weight: 600;">↓ {score:.2f}</span>'
            else:
                return f'<span style="color: #666; font-weight: 600;">• {score:.2f}</span>'
        
        row_bg = '#f8f9fa' if faculties.index(fac) % 2 == 0 else '#ffffff'
        
        table_rows += f"""
                    <tr style="background: {row_bg}; border-bottom: 1px solid #e9ecef;">
                        <td style="padding: 14px; font-weight: 600; color: #2c3e50;">{fac['faculty']} (n={fac['n']})</td>
                        <td style="padding: 14px; text-align: center;">{indicator(fac['vision'], NATIONAL_AVERAGES['Vision'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(fac['effort'], NATIONAL_AVERAGES['Effort'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(fac['systems'], NATIONAL_AVERAGES['Systems'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(fac['practice'], NATIONAL_AVERAGES['Practice'])}</td>
                        <td style="padding: 14px; text-align: center;">{indicator(fac['attitude'], NATIONAL_AVERAGES['Attitude'])}</td>
                        <td style="padding: 14px; text-align: center; background: rgba(220, 20, 60, 0.05); font-size: 1.1em;">{indicator(fac['overall'], NATIONAL_AVERAGES['Overall'])}</td>
                    </tr>
"""
    
    html = f"""
        <div class="section" style="padding: 40px;">
            <h2 style="color: #2c3e50; font-size: 2.2em; margin-bottom: 30px; border-bottom: 3px solid #dc143c; padding-bottom: 15px;">
                Faculty Performance Comparison - Baseline
            </h2>
            <p style="font-size: 1.2em; color: #555; margin-bottom: 40px;">
                Comprehensive VESPA performance metrics across all faculties based on Cycle 1 baseline assessment.
                Student counts reflect total enrollment completing the baseline assessment in each faculty.
            </p>
            
            <div class="faculty-cards-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 25px; margin-bottom: 50px;">
                {faculty_cards}
            </div>
            
            <h3 style="color: #2c3e50; margin-top: 50px; margin-bottom: 15px; font-size: 1.5em;">Detailed Performance Matrix</h3>
            <p style="font-size: 0.95em; color: #666; margin-bottom: 15px;">Compact comparison showing all faculties side-by-side (optimized for print).</p>
            <div style="overflow-x: auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <table style="width: 100%; min-width: 700px; border-collapse: separate; border-spacing: 0; background: white;">
                    <thead>
                        <tr>
                            <th style="background: linear-gradient(135deg, #dc143c, #8b0000); color: white; padding: 18px; text-align: left;">Faculty</th>
                            <th style="background: #e59437; color: white; padding: 18px; text-align: center;">VISION</th>
                            <th style="background: #5690d6; color: white; padding: 18px; text-align: center;">EFFORT</th>
                            <th style="background: #72cb44; color: white; padding: 18px; text-align: center;">SYSTEMS</th>
                            <th style="background: #7f31a4; color: white; padding: 18px; text-align: center;">PRACTICE</th>
                            <th style="background: #f032e6; color: white; padding: 18px; text-align: center;">ATTITUDE</th>
                            <th style="background: linear-gradient(135deg, #dc143c, #8b0000); color: white; padding: 18px; text-align: center; font-weight: bold;">OVERALL</th>
                        </tr>
                    </thead>
                    <tbody>
                    {table_rows}
                    
                    <tr style="background: linear-gradient(135deg, #dc143c, #8b0000); color: white;">
                        <td style="padding: 16px; font-weight: bold;">HARTPURY AVERAGE</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['vision']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['effort']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['systems']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['practice']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold;">{overall['attitude']:.2f}</td>
                        <td style="padding: 16px; text-align: center; font-weight: bold; font-size: 1.1em;">{overall['overall']:.2f}</td>
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
            
            <div class="chart-container">
                <div class="responsive-chart">
                    {faculty_html}
                </div>
            </div>
        </div>
"""
    return html

def generate_gender_section(gender, gender_diffs, gender_html):
    """Generate gender analysis section"""
    
    if len(gender) < 2:
        return ""
    
    male_stats = gender[0] if gender[0]['gender'] == 'Male' else gender[1]
    female_stats = gender[0] if gender[0]['gender'] == 'Female' else gender[1]
    
    # Separate into male-higher and female-higher
    male_higher = [d for d in gender_diffs if d['higher'] == 'Male']
    female_higher = [d for d in gender_diffs if d['higher'] == 'Female']
    
    # Top 3 where males score higher
    male_higher_html = ""
    for i, diff in enumerate(male_higher[:3], 1):
        male_higher_html += f"""
                    <tr>
                        <td style="padding: 10px;">{diff['statement']}</td>
                        <td style="padding: 10px; text-align: center;">{diff['category']}</td>
                        <td style="padding: 10px; text-align: center;"><strong>{diff['male']:.2f}</strong></td>
                        <td style="padding: 10px; text-align: center;">{diff['female']:.2f}</td>
                        <td style="padding: 10px; text-align: center;" class="positive">
                            +{diff['difference']:.2f}<br><small>(Male higher)</small>
                        </td>
                    </tr>
"""
    
    # Top 3 where females score higher
    female_higher_html = ""
    for i, diff in enumerate(female_higher[:3], 1):
        female_higher_html += f"""
                    <tr>
                        <td style="padding: 10px;">{diff['statement']}</td>
                        <td style="padding: 10px; text-align: center;">{diff['category']}</td>
                        <td style="padding: 10px; text-align: center;">{diff['male']:.2f}</td>
                        <td style="padding: 10px; text-align: center;"><strong>{diff['female']:.2f}</strong></td>
                        <td style="padding: 10px; text-align: center;" class="positive">
                            +{diff['difference']:.2f}<br><small>(Female higher)</small>
                        </td>
                    </tr>
"""
    
    html = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #dc143c; padding-bottom: 10px; margin: 0 auto 30px; max-width: 400px;">
                GENDER ANALYSIS
            </h1>
        </div>
        
        <div class="section">
            <h2>👥 VESPA Scores by Gender</h2>
            <p style="margin-bottom: 20px;">
                Analysis of VESPA baseline scores comparing male and female students to identify any gender-specific patterns 
                or support needs. Total sample: {male_stats['n']} male and {female_stats['n']} female students.
            </p>
            
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));">
                <div class="stat-card">
                    <h4>Male Students</h4>
                    <div class="value">{male_stats['overall']:.2f}</div>
                    <small>Overall Score (n={male_stats['n']})</small>
                </div>
                <div class="stat-card">
                    <h4>Female Students</h4>
                    <div class="value">{female_stats['overall']:.2f}</div>
                    <small>Overall Score (n={female_stats['n']})</small>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #28a745, #20c997);">
                    <h4>Difference</h4>
                    <div class="value">{abs(male_stats['overall'] - female_stats['overall']):.2f}</div>
                    <small>({'Minimal' if abs(male_stats['overall'] - female_stats['overall']) < 0.1 else 'Moderate' if abs(male_stats['overall'] - female_stats['overall']) < 0.2 else 'Notable'})</small>
                </div>
            </div>
            
            <div class="chart-container">
                <div class="responsive-chart">
                    {gender_html}
                </div>
            </div>
            
            <h3>Statement-Level Gender Differences</h3>
            <p style="margin: 15px 0;">
                The following statements show the largest differences in agreement between male and female students,
                highlighting areas where gender-specific support or interventions may be beneficial. 
                We show both where males score higher and where females score higher for balanced insight.
            </p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                <div>
                    <h4 style="color: #2c3e50; margin-bottom: 15px; background: rgba(102, 126, 234, 0.1); padding: 10px; border-radius: 5px;">
                        🔵 Top 3 - Male Students Score Higher
                    </h4>
                    <table style="width: 100%;">
                        <thead>
                            <tr>
                                <th style="font-size: 0.85em;">Statement</th>
                                <th style="text-align: center; font-size: 0.85em;">Category</th>
                                <th style="text-align: center; font-size: 0.85em;">Male</th>
                                <th style="text-align: center; font-size: 0.85em;">Female</th>
                                <th style="text-align: center; font-size: 0.85em;">Diff</th>
                            </tr>
                        </thead>
                        <tbody>
                            {male_higher_html}
                        </tbody>
                    </table>
                </div>
                
                <div>
                    <h4 style="color: #2c3e50; margin-bottom: 15px; background: rgba(240, 50, 230, 0.1); padding: 10px; border-radius: 5px;">
                        🟣 Top 3 - Female Students Score Higher
                    </h4>
                    <table style="width: 100%;">
                        <thead>
                            <tr>
                                <th style="font-size: 0.85em;">Statement</th>
                                <th style="text-align: center; font-size: 0.85em;">Category</th>
                                <th style="text-align: center; font-size: 0.85em;">Male</th>
                                <th style="text-align: center; font-size: 0.85em;">Female</th>
                                <th style="text-align: center; font-size: 0.85em;">Diff</th>
                            </tr>
                        </thead>
                        <tbody>
                            {female_higher_html}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h4>Gender Analysis Insights</h4>
                <ul style="margin-top: 10px;">
                    <li><strong>Overall Comparison:</strong> {'Male students score slightly higher' if male_stats['overall'] > female_stats['overall'] else 'Female students score slightly higher'} 
                        ({max(male_stats['overall'], female_stats['overall']):.2f} vs {min(male_stats['overall'], female_stats['overall']):.2f})</li>
                    <li><strong>Males Score Higher On:</strong> "{male_higher[0]['statement']}" ({male_higher[0]['category']}) - {male_higher[0]['difference']:.2f} point difference, 
                        suggesting males show stronger {male_higher[0]['category'].lower()} in this area</li>
                    <li><strong>Females Score Higher On:</strong> "{female_higher[0]['statement']}" ({female_higher[0]['category']}) - {female_higher[0]['difference']:.2f} point difference, 
                        suggesting females demonstrate stronger {female_higher[0]['category'].lower()} in this area</li>
                    <li><strong>Implication:</strong> {'Both genders show similar overall VESPA profiles with minimal intervention needed' if abs(male_stats['overall'] - female_stats['overall']) < 0.1 else 'Consider gender-responsive teaching strategies for areas with larger differences'}, 
                        but note specific strengths of each group for peer mentoring opportunities</li>
                </ul>
            </div>
        </div>
"""
    return html

def generate_residential_section(residential, residential_diffs, residential_html):
    """Generate residential analysis section"""
    
    if len(residential) < 2:
        return ""
    
    res_stats = residential[0] if residential[0]['status'] == 'Residential' else residential[1]
    nonres_stats = residential[0] if residential[0]['status'] == 'Non-Residential' else residential[1]
    
    # Separate into residential-higher and non-residential-higher
    res_higher = [d for d in residential_diffs if d['higher'] == 'Residential']
    nonres_higher = [d for d in residential_diffs if d['higher'] == 'Non-Residential']
    
    # Top 3 where residential scores higher
    res_higher_html = ""
    for i, diff in enumerate(res_higher[:3], 1):
        res_higher_html += f"""
                    <tr>
                        <td style="padding: 10px;">{diff['statement']}</td>
                        <td style="padding: 10px; text-align: center;">{diff['category']}</td>
                        <td style="padding: 10px; text-align: center;"><strong>{diff['residential']:.2f}</strong></td>
                        <td style="padding: 10px; text-align: center;">{diff['non_residential']:.2f}</td>
                        <td style="padding: 10px; text-align: center;" class="positive">
                            +{diff['difference']:.2f}<br><small>(Residential)</small>
                        </td>
                    </tr>
"""
    
    # Top 3 where non-residential scores higher
    nonres_higher_html = ""
    for i, diff in enumerate(nonres_higher[:3], 1):
        nonres_higher_html += f"""
                    <tr>
                        <td style="padding: 10px;">{diff['statement']}</td>
                        <td style="padding: 10px; text-align: center;">{diff['category']}</td>
                        <td style="padding: 10px; text-align: center;">{diff['residential']:.2f}</td>
                        <td style="padding: 10px; text-align: center;"><strong>{diff['non_residential']:.2f}</strong></td>
                        <td style="padding: 10px; text-align: center;" class="positive">
                            +{diff['difference']:.2f}<br><small>(Non-Residential)</small>
                        </td>
                    </tr>
"""
    
    html = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #dc143c; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                RESIDENTIAL STATUS ANALYSIS
            </h1>
        </div>
        
        <div class="section">
            <h2>🏠 VESPA Scores by Residential Status</h2>
            <p style="margin-bottom: 20px;">
                Analysis of VESPA baseline scores comparing residential and non-residential students to understand 
                how living arrangements correlate with learning mindsets and study skills.
                Total sample: {res_stats['n']} residential and {nonres_stats['n']} non-residential students.
            </p>
            
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));">
                <div class="stat-card">
                    <h4>Residential Students</h4>
                    <div class="value">{res_stats['overall']:.2f}</div>
                    <small>Overall Score (n={res_stats['n']})</small>
                </div>
                <div class="stat-card">
                    <h4>Non-Residential Students</h4>
                    <div class="value">{nonres_stats['overall']:.2f}</div>
                    <small>Overall Score (n={nonres_stats['n']})</small>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #28a745, #20c997);">
                    <h4>Difference</h4>
                    <div class="value">{abs(res_stats['overall'] - nonres_stats['overall']):.2f}</div>
                    <small>({'Minimal' if abs(res_stats['overall'] - nonres_stats['overall']) < 0.1 else 'Moderate' if abs(res_stats['overall'] - nonres_stats['overall']) < 0.2 else 'Notable'})</small>
                </div>
            </div>
            
            <div class="chart-container">
                <div class="responsive-chart">
                    {residential_html}
                </div>
            </div>
            
            <h3>Statement-Level Residential Differences</h3>
            <p style="margin: 15px 0;">
                The following statements show the largest differences between residential and non-residential students,
                providing insights into how living arrangements may influence student mindsets and behaviors.
                We show both where residential students score higher and where non-residential students score higher for balanced insight.
            </p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                <div>
                    <h4 style="color: #2c3e50; margin-bottom: 15px; background: rgba(114, 203, 68, 0.1); padding: 10px; border-radius: 5px;">
                        🟢 Top 3 - Residential Students Score Higher
                    </h4>
                    <table style="width: 100%;">
                        <thead>
                            <tr>
                                <th style="font-size: 0.85em;">Statement</th>
                                <th style="text-align: center; font-size: 0.85em;">Category</th>
                                <th style="text-align: center; font-size: 0.85em;">Res</th>
                                <th style="text-align: center; font-size: 0.85em;">Non-Res</th>
                                <th style="text-align: center; font-size: 0.85em;">Diff</th>
                            </tr>
                        </thead>
                        <tbody>
                            {res_higher_html}
                        </tbody>
                    </table>
                </div>
                
                <div>
                    <h4 style="color: #2c3e50; margin-bottom: 15px; background: rgba(229, 148, 55, 0.1); padding: 10px; border-radius: 5px;">
                        🟠 Top 3 - Non-Residential Students Score Higher
                    </h4>
                    <table style="width: 100%;">
                        <thead>
                            <tr>
                                <th style="font-size: 0.85em;">Statement</th>
                                <th style="text-align: center; font-size: 0.85em;">Category</th>
                                <th style="text-align: center; font-size: 0.85em;">Res</th>
                                <th style="text-align: center; font-size: 0.85em;">Non-Res</th>
                                <th style="text-align: center; font-size: 0.85em;">Diff</th>
                            </tr>
                        </thead>
                        <tbody>
                            {nonres_higher_html}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h4>Residential Analysis Insights</h4>
                <ul style="margin-top: 10px;">
                    <li><strong>Overall Comparison:</strong> {'Residential students score higher' if res_stats['overall'] > nonres_stats['overall'] else 'Non-residential students score higher'} 
                        ({max(res_stats['overall'], nonres_stats['overall']):.2f} vs {min(res_stats['overall'], nonres_stats['overall']):.2f})</li>
                    <li><strong>Residential Students Excel At:</strong> "{res_higher[0]['statement']}" ({res_higher[0]['category']}) - {res_higher[0]['difference']:.2f} point higher, 
                        suggesting residential life may provide supportive environment for {res_higher[0]['category'].lower()}</li>
                    <li><strong>Non-Residential Students Excel At:</strong> "{nonres_higher[0]['statement']}" ({nonres_higher[0]['category']}) - {nonres_higher[0]['difference']:.2f} point higher, 
                        indicating strong independent {nonres_higher[0]['category'].lower()} skills</li>
                    <li><strong>Implication:</strong> {'Both groups show similar patterns suggesting universal support strategies are appropriate' if abs(res_stats['overall'] - nonres_stats['overall']) < 0.15 else 'Consider targeted support strategies that account for different living situations'}, 
                        while recognizing unique strengths of each group</li>
                </ul>
            </div>
        </div>
"""
    return html

def generate_statement_section(statements):
    """Generate statement-level analysis section"""
    
    # Top 5 statements
    top_5_html = ""
    for i, stmt in enumerate(statements[:5], 1):
        # Use variance directly from the statement dict
        variance = stmt.get('variance', 0)
        variance_text = "High" if variance > 1.5 else "Moderate" if variance > 0.8 else "Low"
        
        top_5_html += f"""
                        <li style="margin-bottom: 15px; color: #333;">
                            <strong>{stmt['statement']}</strong>
                            <br>
                            <span style="color: #666; font-size: 0.9em;">
                                Mean Score: {stmt['mean']:.2f} | Category: {stmt['category']} | n={stmt['n']}
                                <br>Variance: {variance:.2f} ({variance_text} - {'Consistent agreement' if variance < 1.0 else 'Mixed responses'})
                            </span>
                        </li>
"""
    
    # Bottom 5 statements
    bottom_5_html = ""
    for i, stmt in enumerate(statements[-5:], 1):
        variance = stmt.get('variance', 0)
        variance_text = "High" if variance > 1.5 else "Moderate" if variance > 0.8 else "Low"
        
        bottom_5_html += f"""
                        <li style="margin-bottom: 15px; color: #333;">
                            <strong>{stmt['statement']}</strong>
                            <br>
                            <span style="color: #666; font-size: 0.9em;">
                                Mean Score: {stmt['mean']:.2f} | Category: {stmt['category']} | n={stmt['n']}
                                <br>Variance: {variance:.2f} ({variance_text} - {'Consistent agreement' if variance < 1.0 else 'Mixed responses'})
                            </span>
                        </li>
"""
    
    html = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #dc143c; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                STATEMENT LEVEL ANALYSIS
            </h1>
        </div>
        
        <div class="section">
            <h2>📝 VESPA Statement Analysis - Baseline</h2>
            <p style="margin-bottom: 20px;">
                Detailed analysis of individual VESPA statement responses reveals specific strengths and development areas.
                Each statement is scored on a scale where higher scores indicate stronger agreement/engagement.
            </p>
            
            <div style="margin-top: 50px; padding: 30px; background: linear-gradient(to right, #f8f9fa, #ffffff); border-radius: 12px; border: 1px solid #e9ecef;">
                <h3 style="color: #2c3e50; margin-bottom: 25px; font-size: 1.6em;">Statement Agreement Analysis</h3>
                <p style="color: #666; margin-bottom: 30px;">Analysis of which statements students most and least agree with in the baseline assessment.</p>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                    <div style="background: #fff; padding: 25px; border-radius: 10px; border: 2px solid #28a745;">
                        <h4 style="color: #28a745; margin-bottom: 20px; font-size: 1.2em;">Top 5 - Students Strongly Agree</h4>
                        <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">
                            {top_5_html}
                        </ol>
                    </div>
                    
                    <div style="background: #fff; padding: 25px; border-radius: 10px; border: 2px solid #dc3545;">
                        <h4 style="color: #dc3545; margin-bottom: 20px; font-size: 1.2em;">Bottom 5 - Development Opportunities</h4>
                        <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">
                            {bottom_5_html}
                        </ol>
                    </div>
                </div>
                
                <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <h4 style="color: #2c3e50; margin-bottom: 10px;">Interpretation Guide</h4>
                    <p style="margin: 0 0 10px 0; font-size: 0.95em; color: #555;">
                        <strong>Mean Scores:</strong> Statements range from 1-5. Scores above 4.0 indicate strong agreement, 
                        scores between 3.0-4.0 show moderate agreement, and scores below 3.0 suggest areas where students lack confidence 
                        or need additional support.
                    </p>
                    <p style="margin: 0; font-size: 0.95em; color: #555;">
                        <strong>Variance:</strong> Measures how spread out student responses are. <em>Low variance</em> (below 0.8) means 
                        most students agree and responses are consistent - ideal for building on strengths or addressing common challenges. 
                        <em>High variance</em> (above 1.5) indicates mixed responses where some students strongly agree while others don't - 
                        suggesting differentiated support may be needed. <em>Moderate variance</em> (0.8-1.5) shows typical spread in student experiences.
                    </p>
                </div>
            </div>
        </div>
"""
    return html

def generate_year_group_section(year_groups, year_group_html):
    """Generate year group analysis section"""
    
    if len(year_groups) == 0:
        return ""
    
    # Generate year group cards
    yg_cards = ""
    for idx, yg in enumerate(year_groups, 1):
        # Determine badge color based on performance
        if idx <= 2:
            badge_color = '#28a745'
        elif idx >= len(year_groups) - 1:
            badge_color = '#dc3545'
        else:
            badge_color = '#dc143c'
        
        yg_cards += f"""
                <div class="stat-card">
                    <h4>Year {yg['year_group']}</h4>
                    <div class="value">{yg['overall']:.2f}</div>
                    <small>n={yg['n']} students</small>
                    <div style="margin-top: 8px; font-size: 0.75em;">
                        Rank: #{idx} of {len(year_groups)}
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
                        <td style="padding: 12px; text-align: center; font-weight: bold; background: rgba(220, 20, 60, 0.05);">{yg['overall']:.2f}</td>
                    </tr>
"""
    
    html = f"""
        <div style="background: #f0f4f8; padding: 30px 0; margin-top: 30px;">
            <h1 style="text-align: center; color: #2c3e50; border-bottom: 3px solid #dc143c; padding-bottom: 10px; margin: 0 auto 30px; max-width: 500px;">
                YEAR GROUP ANALYSIS
            </h1>
        </div>
        
        <div class="section">
            <h2>📚 VESPA Scores by Year Group</h2>
            <p style="margin-bottom: 20px;">
                Analysis of VESPA baseline scores across different year groups to identify cohort-specific patterns.
                Year groups are compared to understand how students at different stages of their educational journey 
                engage with VESPA dimensions.
            </p>
            
            <h3>Year Group Performance Overview</h3>
            <div class="stats-grid">
                {yg_cards}
            </div>
            
            <div class="chart-container">
                <div class="responsive-chart">
                    {year_group_html if year_group_html else '<p>No year group comparison chart available.</p>'}
                </div>
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
                    <li><strong>Development Focus:</strong> Year {year_groups[-1]['year_group']} shows opportunity for targeted support at {year_groups[-1]['overall']:.2f} (n={year_groups[-1]['n']} students)</li>
                    <li><strong>Cohort Planning:</strong> Use these baseline differences to tailor intervention strategies by year group as students progress through Cycle 2 and 3</li>
                </ul>
            </div>
        </div>
"""
    return html

def generate_footer():
    """Generate report footer"""
    return """
        <div class="footer">
            <p>© 2024 VESPA Education Analytics | Hartpury University - Confidential Report</p>
            <p style="margin-top: 10px; font-size: 0.9em;">Cycle 1 Baseline | Academic Year 2024/25</p>
        </div>
"""

# Import Path for file operations
from pathlib import Path

def main():
    csv_path = r"C:\Users\tonyd\OneDrive - 4Sight Education Ltd\Apps\DASHBOARD\DASHBOARD\HartpuryCycle12025.csv"
    
    try:
        df = load_data(csv_path)
        filename = generate_html_report(df)
        return filename
    except Exception as e:
        print(f"\n❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    main()

