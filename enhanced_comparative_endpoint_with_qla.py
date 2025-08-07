"""
Enhanced Comparative Report Endpoint with Question Level Analysis
This replaces/enhances the previous comparative report endpoint
"""

def fetch_question_level_data(establishment_id, report_type, config):
    """
    Fetch question-level data for comparative analysis
    """
    try:
        if report_type == 'cycle_progression':
            cycles = config.get('cycles', [])
            question_data = {}
            
            for cycle in cycles:
                # Get question responses for this cycle
                result = supabase.table('question_responses') \
                    .select('*, students!inner(establishment_id), questions!inner(question_text, vespa_category)') \
                    .eq('students.establishment_id', establishment_id) \
                    .eq('cycle', cycle) \
                    .execute()
                
                if result.data:
                    # Group by question_id and calculate stats
                    questions_stats = {}
                    for response in result.data:
                        q_id = response['question_id']
                        if q_id not in questions_stats:
                            questions_stats[q_id] = {
                                'responses': [],
                                'text': response['questions']['question_text'],
                                'category': response['questions']['vespa_category']
                            }
                        questions_stats[q_id]['responses'].append(response['response_value'])
                    
                    # Calculate statistics
                    for q_id, data in questions_stats.items():
                        responses = data['responses']
                        questions_stats[q_id]['mean'] = np.mean(responses)
                        questions_stats[q_id]['std'] = np.std(responses)
                        questions_stats[q_id]['count'] = len(responses)
                        questions_stats[q_id]['distribution'] = calculate_distribution(responses)
                    
                    question_data[f'cycle_{cycle}'] = questions_stats
            
            return analyze_question_differences(question_data)
            
        elif report_type == 'group_comparison':
            dimension = config.get('groupDimension')
            groups = config.get('groups', [])
            question_data = {}
            
            for group in groups:
                # Get question responses for this group
                if dimension == 'year_group':
                    result = supabase.table('question_responses') \
                        .select('*, students!inner(year_group, establishment_id), questions!inner(question_text, vespa_category)') \
                        .eq('students.establishment_id', establishment_id) \
                        .eq('students.year_group', group) \
                        .execute()
                # Add other dimension queries as needed
                
                if result.data:
                    # Similar processing as above
                    questions_stats = process_question_responses(result.data)
                    question_data[group] = questions_stats
            
            return analyze_question_differences(question_data)
            
    except Exception as e:
        app.logger.error(f"Failed to fetch question data: {e}")
        return {}

def calculate_distribution(responses):
    """Calculate percentage distribution of responses (1-5 scale)"""
    distribution = [0] * 5
    total = len(responses)
    
    if total == 0:
        return distribution
        
    for r in responses:
        if 1 <= r <= 5:
            distribution[r - 1] += 1
    
    # Convert to percentages
    return [round((count / total) * 100, 1) for count in distribution]

def analyze_question_differences(question_data):
    """
    Analyze differences between groups at question level
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
        
        # Calculate statistical measures
        difference = g2['mean'] - g1['mean']
        
        # Cohen's d effect size
        pooled_std = np.sqrt((g1['std']**2 + g2['std']**2) / 2)
        cohens_d = difference / pooled_std if pooled_std > 0 else 0
        
        # Simple t-test approximation (would use scipy.stats for real implementation)
        standard_error = pooled_std * np.sqrt(1/g1['count'] + 1/g2['count'])
        t_stat = difference / standard_error if standard_error > 0 else 0
        # Approximate p-value (would use proper distribution)
        p_value = 2 * (1 - stats.norm.cdf(abs(t_stat))) if 'stats' in globals() else 0.05
        
        analyzed_questions.append({
            'id': q_id,
            'text': g1['text'],
            'category': g1['category'],
            'group1Score': g1['mean'],
            'group2Score': g2['mean'],
            'difference': difference,
            'cohensD': cohens_d,
            'pValue': p_value,
            'group1Distribution': g1['distribution'],
            'group2Distribution': g2['distribution'],
            'group1Count': g1['count'],
            'group2Count': g2['count']
        })
    
    # Sort by absolute difference
    analyzed_questions.sort(key=lambda x: abs(x['difference']), reverse=True)
    
    return {
        'questions': analyzed_questions,
        'totalQuestions': len(analyzed_questions),
        'significantDifferences': sum(1 for q in analyzed_questions if q['pValue'] < 0.05)
    }

def generate_qla_insights(question_data, context):
    """
    Generate AI insights specifically for question-level analysis
    """
    if not OPENAI_API_KEY or not question_data.get('questions'):
        return []
    
    try:
        # Identify key patterns
        top_differences = question_data['questions'][:5]
        by_category = {}
        
        for q in question_data['questions']:
            cat = q['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(q['difference'])
        
        category_means = {cat: np.mean(diffs) for cat, diffs in by_category.items()}
        
        prompt = f"""
        Analyze these question-level differences:
        
        TOP DIFFERENCES:
        {[f"{q['text']}: Δ={q['difference']:.2f}" for q in top_differences]}
        
        CATEGORY PATTERNS:
        {category_means}
        
        CONTEXT: {context}
        
        Provide 3-4 specific insights about:
        1. What the question-level patterns reveal
        2. Why certain questions show larger differences
        3. Actionable recommendations based on specific questions
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are analyzing question-level assessment data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        insights_text = response.choices[0].message['content']
        # Parse into bullet points
        return insights_text.split('\n')
        
    except Exception as e:
        app.logger.error(f"QLA insights generation failed: {e}")
        return []

# Enhanced main endpoint
@app.route('/api/comparative-report', methods=['POST'])
def generate_comparative_report():
    """Generate a comprehensive comparative report with QLA"""
    try:
        data = request.get_json()
        
        # ... [Previous extraction code] ...
        
        # Fetch VESPA comparison data
        comparison_data = fetch_comparison_data(
            establishment_id, 
            report_type, 
            config
        )
        
        # NEW: Fetch question-level data
        question_data = fetch_question_level_data(
            establishment_id,
            report_type,
            config
        )
        
        # Generate AI insights with both VESPA and QLA data
        ai_insights = generate_contextual_insights(
            comparison_data,
            question_data,  # Pass QLA data
            organizational_context,
            specific_questions,
            historical_context,
            report_type,
            establishment_name
        )
        
        # Generate QLA-specific insights
        qla_insights = generate_qla_insights(
            question_data,
            organizational_context
        )
        
        # Add QLA insights to question data
        if question_data:
            question_data['insights'] = qla_insights
        
        # Create enhanced PDF with QLA section
        pdf_buffer = create_enhanced_pdf_with_qla(
            establishment_name,
            establishment_logo_url,
            primary_color,
            comparison_data,
            question_data,  # Include QLA data
            ai_insights,
            config
        )
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Comparative_Report_{establishment_name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Failed to generate comparative report: {e}")
        raise ApiError(f"Report generation failed: {str(e)}", 500)

def create_enhanced_pdf_with_qla(school_name, logo_url, primary_color, vespa_data, qla_data, insights, config):
    """
    Create PDF with enhanced visualizations and QLA section
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.legends import Legend
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # ... [Previous header code] ...
    
    # NEW: Question Level Analysis Section
    if qla_data and qla_data.get('questions'):
        elements.append(PageBreak())
        elements.append(Paragraph("<b>Question Level Analysis</b>", styles['Heading1']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Top differences table
        elements.append(Paragraph("<b>Questions with Largest Differences</b>", styles['Heading2']))
        
        qla_table_data = [['Question', 'Category', 'Group 1', 'Group 2', 'Difference', 'Significance']]
        
        for q in qla_data['questions'][:10]:
            significance = '***' if q['pValue'] < 0.001 else '**' if q['pValue'] < 0.01 else '*' if q['pValue'] < 0.05 else ''
            qla_table_data.append([
                q['text'][:50] + '...' if len(q['text']) > 50 else q['text'],
                q['category'],
                f"{q['group1Score']:.2f}",
                f"{q['group2Score']:.2f}",
                f"{q['difference']:+.2f}",
                significance
            ])
        
        qla_table = Table(qla_table_data)
        qla_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(qla_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # QLA Insights
        if qla_data.get('insights'):
            elements.append(Paragraph("<b>Question-Level Insights</b>", styles['Heading2']))
            for insight in qla_data['insights'][:5]:
                elements.append(Paragraph(f"• {insight}", styles['BodyText']))
            elements.append(Spacer(1, 0.3*inch))
        
        # Visual representation of distribution differences
        # This would include charts generated from the question distribution data
        
    # ... [Rest of PDF generation] ...
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
