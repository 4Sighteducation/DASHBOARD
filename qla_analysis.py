"""
Question Level Analysis Module for Comparative Reports
This module handles all question-level data fetching and statistical analysis
"""

import numpy as np
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import scipy.stats as stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available - statistical tests will be limited")


def fetch_question_level_data(supabase_client, establishment_id: str, report_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch question-level response data for comparative analysis
    
    Args:
        supabase_client: Supabase client instance
        establishment_id: UUID of the establishment
        report_type: Type of comparison (cycle_vs_cycle, year_group_vs_year_group, etc.)
        config: Configuration containing comparison parameters
        
    Returns:
        Dictionary containing analyzed question data
    """
    try:
        if report_type == 'cycle_vs_cycle':
            cycle1 = int(config.get('cycle1', 1))
            cycle2 = int(config.get('cycle2', 2))
            academic_year = config.get('academicYear')
            year_group = config.get('yearGroup') or config.get('year_group')

            # Optional gender comparisons (requested for Rochdale: Cycle 1 vs Cycle 2 by gender)
            include_gender = bool(config.get('includeGenderComparisons', True))
            genders = config.get('genders') or ['Female', 'Male']

            overall1 = fetch_cycle_responses(
                supabase_client,
                establishment_id,
                cycle1,
                academic_year=academic_year,
                year_group=year_group,
                gender=None,
            )
            overall2 = fetch_cycle_responses(
                supabase_client,
                establishment_id,
                cycle2,
                academic_year=academic_year,
                year_group=year_group,
                gender=None,
            )

            result: Dict[str, Any] = {
                'overall': analyze_question_differences(
                    {f'cycle_{cycle1}': overall1, f'cycle_{cycle2}': overall2},
                    f'Cycle {cycle1}',
                    f'Cycle {cycle2}',
                )
            }

            if include_gender:
                by_gender: Dict[str, Any] = {}
                for g in genders:
                    g1 = fetch_cycle_responses(
                        supabase_client,
                        establishment_id,
                        cycle1,
                        academic_year=academic_year,
                        year_group=year_group,
                        gender=g,
                    )
                    g2 = fetch_cycle_responses(
                        supabase_client,
                        establishment_id,
                        cycle2,
                        academic_year=academic_year,
                        year_group=year_group,
                        gender=g,
                    )

                    # Only include if we have data for both cycles
                    if g1 and g2:
                        by_gender[g] = analyze_question_differences(
                            {f'cycle_{cycle1}': g1, f'cycle_{cycle2}': g2},
                            f'Cycle {cycle1} ({g})',
                            f'Cycle {cycle2} ({g})',
                        )

                if by_gender:
                    result['by_gender'] = by_gender

            return result

        if report_type == 'year_group_vs_year_group':
            year_group1 = config.get('yearGroup1')
            year_group2 = config.get('yearGroup2')
            cycle = int(config.get('cycle', 1))
            academic_year = config.get('academicYear')

            data1 = fetch_year_group_responses(supabase_client, establishment_id, year_group1, cycle, academic_year)
            data2 = fetch_year_group_responses(supabase_client, establishment_id, year_group2, cycle, academic_year)

            return analyze_question_differences(
                {f'year_{year_group1}': data1, f'year_{year_group2}': data2},
                f'Year {year_group1}',
                f'Year {year_group2}',
            )

        if report_type == 'academic_year_vs_academic_year':
            year1 = config.get('academicYear1')
            year2 = config.get('academicYear2')
            year_group = config.get('yearGroup')
            cycle = int(config.get('cycle', 1))

            data1 = fetch_academic_year_responses(supabase_client, establishment_id, year1, year_group, cycle)
            data2 = fetch_academic_year_responses(supabase_client, establishment_id, year2, year_group, cycle)

            return analyze_question_differences(
                {f'year_{year1}': data1, f'year_{year2}': data2},
                str(year1),
                str(year2),
            )

        if report_type == 'faculty_vs_faculty':
            faculty1 = config.get('faculty1')
            faculty2 = config.get('faculty2')
            cycle = int(config.get('cycle', 1))
            academic_year = config.get('academicYear')

            faculty1_students = supabase_client.table('students')\
                .select('id')\
                .eq('establishment_id', establishment_id)\
                .eq('faculty', faculty1)
            if academic_year:
                faculty1_students = faculty1_students.eq('academic_year', academic_year)
            faculty1_result = faculty1_students.execute()
            faculty1_ids = [s['id'] for s in faculty1_result.data] if faculty1_result.data else []

            faculty2_students = supabase_client.table('students')\
                .select('id')\
                .eq('establishment_id', establishment_id)\
                .eq('faculty', faculty2)
            if academic_year:
                faculty2_students = faculty2_students.eq('academic_year', academic_year)
            faculty2_result = faculty2_students.execute()
            faculty2_ids = [s['id'] for s in faculty2_result.data] if faculty2_result.data else []

            if not faculty1_ids or not faculty2_ids:
                return {}

            faculty1_responses = supabase_client.table('question_responses')\
                .select('*')\
                .in_('student_id', faculty1_ids)\
                .eq('cycle', cycle)
            if academic_year:
                faculty1_responses = faculty1_responses.eq('academic_year', academic_year)
            faculty1_data = faculty1_responses.execute()

            faculty2_responses = supabase_client.table('question_responses')\
                .select('*')\
                .in_('student_id', faculty2_ids)\
                .eq('cycle', cycle)
            if academic_year:
                faculty2_responses = faculty2_responses.eq('academic_year', academic_year)
            faculty2_data = faculty2_responses.execute()

            question_data: Dict[str, Any] = {}
            for resp in (faculty1_data.data or []):
                q_id = resp['question_id']
                if q_id not in question_data:
                    question_data[q_id] = {f'faculty_{faculty1}': [], f'faculty_{faculty2}': []}
                question_data[q_id][f'faculty_{faculty1}'].append(resp['response_value'])

            for resp in (faculty2_data.data or []):
                q_id = resp['question_id']
                if q_id not in question_data:
                    question_data[q_id] = {f'faculty_{faculty1}': [], f'faculty_{faculty2}': []}
                question_data[q_id][f'faculty_{faculty2}'].append(resp['response_value'])

            return question_data

        if report_type == 'faculty_progression':
            faculty = config.get('faculty')
            academic_years = config.get('academicYears', [])
            cycles = config.get('cycles', [1, 2])

            question_data: Dict[str, Any] = {}

            for year in academic_years:
                for cycle in cycles:
                    students_query = supabase_client.table('students')\
                        .select('id')\
                        .eq('establishment_id', establishment_id)\
                        .eq('faculty', faculty)\
                        .eq('academic_year', year)
                    students_result = students_query.execute()
                    student_ids = [s['id'] for s in students_result.data] if students_result.data else []

                    if student_ids:
                        responses = supabase_client.table('question_responses')\
                            .select('*')\
                            .in_('student_id', student_ids)\
                            .eq('cycle', cycle)\
                            .eq('academic_year', year)\
                            .execute()

                        key = f"faculty_{faculty}_year_{year.replace('/', '_')}_cycle_{cycle}"
                        for resp in (responses.data or []):
                            q_id = resp['question_id']
                            if q_id not in question_data:
                                question_data[q_id] = {}
                            if key not in question_data[q_id]:
                                question_data[q_id][key] = []
                            question_data[q_id][key].append(resp['response_value'])

            return question_data

        if report_type == 'cohort_progression':
            starting_year_group = config.get('startingYearGroup')
            starting_academic_year = config.get('startingAcademicYear')
            years_to_track = int(config.get('yearsToTrack', 2))

            cohort_data = track_cohort_responses(
                supabase_client,
                establishment_id,
                starting_year_group,
                starting_academic_year,
                years_to_track,
            )

            return analyze_cohort_progression(cohort_data)

        logger.warning(f"Unsupported report type for QLA: {report_type}")
        return {}

    except Exception as e:
        logger.error(f"Failed to fetch question level data: {e}")
        return {}


def fetch_cycle_responses(
    supabase_client,
    establishment_id: str,
    cycle: int,
    academic_year: Optional[str] = None,
    year_group: Optional[str] = None,
    gender: Optional[str] = None,
) -> Dict:
    """Fetch question responses for a specific cycle"""
    try:
        # Get all questions
        questions_result = supabase_client.table('questions')\
            .select('*')\
            .eq('is_active', True)\
            .execute()
        
        questions = questions_result.data if questions_result.data else []
        
        # Get students for this establishment (paginate: Supabase defaults to 1000 rows)
        base_students_query = supabase_client.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)
        
        if academic_year:
            base_students_query = base_students_query.eq('academic_year', academic_year)
        if year_group:
            base_students_query = base_students_query.eq('year_group', str(year_group))
        if gender:
            # Best-effort: some DBs do not have students.gender
            base_students_query = base_students_query.eq('gender', str(gender))

        def _fetch_all_student_ids(q):
            all_rows = []
            page_size = 1000
            start = 0
            while True:
                res = q.range(start, start + page_size - 1).execute()
                rows = res.data or []
                all_rows.extend(rows)
                if len(rows) < page_size:
                    break
                start += page_size
            return [r['id'] for r in all_rows if r.get('id')]

        try:
            student_ids = _fetch_all_student_ids(base_students_query)
        except Exception as e:
            # Retry without gender filter if column doesn't exist
            if gender and 'gender' in str(e).lower():
                logger.warning("students.gender not available; retrying without gender filter")
                students_query = supabase_client.table('students')\
                    .select('id')\
                    .eq('establishment_id', establishment_id)
                if academic_year:
                    students_query = students_query.eq('academic_year', academic_year)
                if year_group:
                    students_query = students_query.eq('year_group', str(year_group))
                student_ids = _fetch_all_student_ids(students_query)
            else:
                raise
        
        if not student_ids:
            return {}
        
        # Get question responses for these students and cycle (batch student_ids to avoid URL limits)
        responses = []
        batch_size = 50
        for i in range(0, len(student_ids), batch_size):
            batch_ids = student_ids[i:i + batch_size]
            q = supabase_client.table('question_responses')\
                .select('*')\
                .in_('student_id', batch_ids)\
                .eq('cycle', cycle)
            if academic_year:
                q = q.eq('academic_year', academic_year)
            res = q.execute()
            if res.data:
                responses.extend(res.data)
        
        # Organize responses by question
        question_data = {}
        for question in questions:
            # IMPORTANT: question_responses.question_id is a string code (matches questions.question_id),
            # not the UUID primary key questions.id.
            q_code = question.get('question_id')
            if not q_code:
                continue
            q_responses = [r for r in responses if r.get('question_id') == q_code]
            
            if q_responses:
                response_values = [r['response_value'] for r in q_responses if r.get('response_value') is not None]
                if response_values:
                    question_data[q_code] = {
                        'text': question['question_text'],
                        'category': question['vespa_category'],
                        'responses': response_values,
                        'mean': float(np.mean(response_values)),
                        'std': float(np.std(response_values)),
                        'count': len(response_values),
                        'distribution': calculate_distribution(response_values)
                    }
        
        return question_data
        
    except Exception as e:
        logger.error(f"Failed to fetch cycle responses: {e}")
        return {}


def fetch_year_group_responses(supabase_client, establishment_id: str, year_group: str, cycle: int, academic_year: Optional[str] = None) -> Dict:
    """Fetch question responses for a specific year group"""
    try:
        # Get questions
        questions_result = supabase_client.table('questions')\
            .select('*')\
            .eq('is_active', True)\
            .execute()
        
        questions = questions_result.data if questions_result.data else []
        
        # Get students for this year group
        students_query = supabase_client.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)\
            .eq('year_group', year_group)
        
        if academic_year:
            students_query = students_query.eq('academic_year', academic_year)
            
        students_result = students_query.execute()
        student_ids = [s['id'] for s in students_result.data] if students_result.data else []
        
        if not student_ids:
            return {}
        
        # Get responses
        responses_result = supabase_client.table('question_responses')\
            .select('*')\
            .in_('student_id', student_ids)\
            .eq('cycle', cycle)\
            .execute()
        
        responses = responses_result.data if responses_result.data else []
        
        # Process responses by question
        question_data = {}
        for question in questions:
            q_id = question['id']
            q_responses = [r for r in responses if r.get('question_id') == q_id]
            
            if q_responses:
                response_values = [r['response_value'] for r in q_responses if r.get('response_value') is not None]
                if response_values:
                    question_data[q_id] = {
                        'text': question['question_text'],
                        'category': question['vespa_category'],
                        'responses': response_values,
                        'mean': float(np.mean(response_values)),
                        'std': float(np.std(response_values)),
                        'count': len(response_values),
                        'distribution': calculate_distribution(response_values)
                    }
        
        return question_data
        
    except Exception as e:
        logger.error(f"Failed to fetch year group responses: {e}")
        return {}


def fetch_academic_year_responses(supabase_client, establishment_id: str, academic_year: str, year_group: Optional[str] = None, cycle: int = 1) -> Dict:
    """Fetch question responses for a specific academic year"""
    try:
        # Get questions
        questions_result = supabase_client.table('questions')\
            .select('*')\
            .eq('is_active', True)\
            .execute()
        
        questions = questions_result.data if questions_result.data else []
        
        # Get students for this academic year
        students_query = supabase_client.table('students')\
            .select('id')\
            .eq('establishment_id', establishment_id)\
            .eq('academic_year', academic_year)
        
        if year_group:
            students_query = students_query.eq('year_group', year_group)
            
        students_result = students_query.execute()
        student_ids = [s['id'] for s in students_result.data] if students_result.data else []
        
        if not student_ids:
            return {}
        
        # Get responses
        responses_result = supabase_client.table('question_responses')\
            .select('*')\
            .in_('student_id', student_ids)\
            .eq('cycle', cycle)\
            .execute()
        
        responses = responses_result.data if responses_result.data else []
        
        # Process responses
        question_data = {}
        for question in questions:
            q_id = question['id']
            q_responses = [r for r in responses if r.get('question_id') == q_id]
            
            if q_responses:
                response_values = [r['response_value'] for r in q_responses if r.get('response_value') is not None]
                if response_values:
                    question_data[q_id] = {
                        'text': question['question_text'],
                        'category': question['vespa_category'],
                        'responses': response_values,
                        'mean': float(np.mean(response_values)),
                        'std': float(np.std(response_values)),
                        'count': len(response_values),
                        'distribution': calculate_distribution(response_values)
                    }
        
        return question_data
        
    except Exception as e:
        logger.error(f"Failed to fetch academic year responses: {e}")
        return {}


def track_cohort_responses(supabase_client, establishment_id: str, starting_year_group: str, starting_academic_year: str, years_to_track: int) -> Dict:
    """Track a cohort of students across multiple academic years"""
    try:
        # Get initial cohort
        students_result = supabase_client.table('students')\
            .select('id, knack_id, email')\
            .eq('establishment_id', establishment_id)\
            .eq('year_group', starting_year_group)\
            .eq('academic_year', starting_academic_year)\
            .execute()
        
        if not students_result.data:
            return {}
        
        # Track these students across years
        cohort_ids = [s['id'] for s in students_result.data]
        cohort_data = {}
        
        for year_offset in range(years_to_track):
            # Calculate academic year - format is "YYYY/YYYY"
            year_parts = starting_academic_year.split('/')
            if len(year_parts) == 2:
                start_year = int(year_parts[0]) + year_offset
                end_year = int(year_parts[1]) + year_offset
                current_academic_year = f"{start_year}/{end_year}"
            else:
                current_academic_year = starting_academic_year
            
            # Get responses for this year
            responses_result = supabase_client.table('question_responses')\
                .select('*')\
                .in_('student_id', cohort_ids)\
                .execute()
            
            # Process and store
            cohort_data[f'year_{year_offset + 1}'] = process_cohort_year_data(responses_result.data if responses_result.data else [])
        
        return cohort_data
        
    except Exception as e:
        logger.error(f"Failed to track cohort: {e}")
        return {}


def process_cohort_year_data(responses: List[Dict]) -> Dict:
    """Process responses for a cohort year"""
    # Group by question and calculate statistics
    question_groups = {}
    for response in responses:
        q_id = response.get('question_id')
        if q_id:
            if q_id not in question_groups:
                question_groups[q_id] = []
            if response.get('response_value') is not None:
                question_groups[q_id].append(response['response_value'])
    
    return question_groups


def calculate_distribution(responses: List[float]) -> List[float]:
    """Calculate percentage distribution of responses (1-5 Likert scale)"""
    distribution = [0] * 5
    total = len(responses)
    
    if total == 0:
        return distribution
    
    for r in responses:
        if 1 <= r <= 5:
            distribution[int(r) - 1] += 1
    
    # Convert to percentages
    return [round((count / total) * 100, 1) for count in distribution]


def analyze_question_differences(question_data: Dict, group1_label: str, group2_label: str) -> Dict:
    """
    Analyze differences between two groups at question level
    
    Args:
        question_data: Dictionary with group data
        group1_label: Label for first group
        group2_label: Label for second group
        
    Returns:
        Dictionary with analyzed questions and statistics
    """
    groups = list(question_data.keys())
    if len(groups) < 2:
        return {}
    
    group1_data = question_data[groups[0]]
    group2_data = question_data[groups[1]]
    
    analyzed_questions = []
    
    # Find common questions
    common_questions = set(group1_data.keys()) & set(group2_data.keys())
    
    for q_id in common_questions:
        g1 = group1_data[q_id]
        g2 = group2_data[q_id]
        
        # Calculate difference
        difference = g2['mean'] - g1['mean']
        
        # Calculate Cohen's d effect size
        pooled_std = np.sqrt((g1['std']**2 + g2['std']**2) / 2) if g1['std'] > 0 or g2['std'] > 0 else 1
        cohens_d = difference / pooled_std if pooled_std > 0 else 0
        
        # Calculate p-value if scipy available
        if SCIPY_AVAILABLE and len(g1.get('responses', [])) > 1 and len(g2.get('responses', [])) > 1:
            t_stat, p_value = stats.ttest_ind(g1['responses'], g2['responses'])
        else:
            # Approximate p-value using normal distribution
            standard_error = pooled_std * np.sqrt(1/g1['count'] + 1/g2['count']) if pooled_std > 0 else 1
            t_stat = difference / standard_error if standard_error > 0 else 0
            # Very rough approximation
            p_value = 0.05 if abs(t_stat) > 2 else 0.5
        
        analyzed_questions.append({
            'id': q_id,
            'text': g1['text'],
            'category': g1['category'],
            'group1Score': g1['mean'],
            'group2Score': g2['mean'],
            'difference': difference,
            'cohensD': cohens_d,
            'pValue': p_value,
            'tStatistic': t_stat,
            'group1Distribution': g1['distribution'],
            'group2Distribution': g2['distribution'],
            'group1Count': g1['count'],
            'group2Count': g2['count']
        })
    
    # Sort by absolute difference
    analyzed_questions.sort(key=lambda x: abs(x['difference']), reverse=True)
    
    # Generate insights
    insights = generate_qla_insights(analyzed_questions, group1_label, group2_label)
    
    return {
        'questions': analyzed_questions,
        'totalQuestions': len(analyzed_questions),
        'significantDifferences': sum(1 for q in analyzed_questions if q['pValue'] < 0.05),
        'insights': insights,
        'group1Label': group1_label,
        'group2Label': group2_label
    }


def analyze_cohort_progression(cohort_data: Dict) -> Dict:
    """Analyze progression of a cohort over time"""
    # Implementation for cohort progression analysis
    years = sorted(cohort_data.keys())
    
    if len(years) < 2:
        return {}
    
    # Track changes over time
    progression_data = []
    
    # Compare each year to the previous
    for i in range(1, len(years)):
        year1_data = cohort_data[years[i-1]]
        year2_data = cohort_data[years[i]]
        
        # Analyze progression
        # ... (implementation details)
    
    return {
        'progression': progression_data,
        'years': years,
        'insights': []
    }


def generate_qla_insights(questions: List[Dict], group1_label: str, group2_label: str) -> List[str]:
    """Generate insights from question-level analysis"""
    insights = []
    
    if not questions:
        return insights
    
    # Find largest differences
    top_differences = questions[:5]
    
    # Category analysis
    category_diffs = {}
    for q in questions:
        cat = q['category']
        if cat not in category_diffs:
            category_diffs[cat] = []
        category_diffs[cat].append(q['difference'])
    
    # Generate insights
    if top_differences:
        max_diff = top_differences[0]
        insights.append(
            f"{group2_label} scores {'higher' if max_diff['difference'] > 0 else 'lower'} than {group1_label} "
            f"on '{max_diff['text'][:50]}...' by {abs(max_diff['difference']):.2f} points"
        )
    
    # Category insights
    for cat, diffs in category_diffs.items():
        avg_diff = np.mean(diffs)
        if abs(avg_diff) > 0.5:
            insights.append(
                f"{cat.capitalize()} questions show an average difference of {avg_diff:.2f} points "
                f"({'favoring ' + group2_label if avg_diff > 0 else 'favoring ' + group1_label})"
            )
    
    # Statistical significance
    significant_count = sum(1 for q in questions if q['pValue'] < 0.05)
    if significant_count > 0:
        insights.append(
            f"{significant_count} out of {len(questions)} questions show statistically significant differences (p < 0.05)"
        )
    
    # Effect size insights
    large_effects = [q for q in questions if abs(q['cohensD']) > 0.8]
    if large_effects:
        insights.append(
            f"{len(large_effects)} questions show large effect sizes (Cohen's d > 0.8), indicating meaningful practical differences"
        )
    
    return insights[:5]  # Return top 5 insights


def calculate_cohens_d(group1_data: List[float], group2_data: List[float]) -> float:
    """Calculate Cohen's d effect size"""
    n1 = len(group1_data)
    n2 = len(group2_data)
    
    if n1 < 2 or n2 < 2:
        return 0.0
    
    mean1 = np.mean(group1_data)
    mean2 = np.mean(group2_data)
    
    # Pooled standard deviation
    var1 = np.var(group1_data, ddof=1)
    var2 = np.var(group2_data, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return 0.0
    
    return (mean1 - mean2) / pooled_std


def interpret_cohens_d(d: float) -> str:
    """Interpret Cohen's d effect size"""
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"


def calculate_statistical_significance(group1_data: List[float], group2_data: List[float]) -> Dict[str, float]:
    """Calculate statistical significance measures"""
    if SCIPY_AVAILABLE and len(group1_data) > 1 and len(group2_data) > 1:
        # T-test
        t_stat, p_value = stats.ttest_ind(group1_data, group2_data)
        
        # Mann-Whitney U test (non-parametric alternative)
        u_stat, u_p_value = stats.mannwhitneyu(group1_data, group2_data, alternative='two-sided')
        
        # Effect size
        cohens_d = calculate_cohens_d(group1_data, group2_data)
        
        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'u_statistic': u_stat,
            'u_p_value': u_p_value,
            'cohens_d': cohens_d,
            'effect_size': interpret_cohens_d(cohens_d)
        }
    else:
        # Basic statistics without scipy
        mean1 = np.mean(group1_data)
        mean2 = np.mean(group2_data)
        std1 = np.std(group1_data)
        std2 = np.std(group2_data)
        
        return {
            'mean_difference': mean2 - mean1,
            'std1': std1,
            'std2': std2,
            'cohens_d': calculate_cohens_d(group1_data, group2_data)
        }
