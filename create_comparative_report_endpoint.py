"""
Enhanced Comparative Report Endpoint with Context-Aware AI
Add this to your app.py file
"""

@app.route('/api/comparative-report', methods=['POST'])
def generate_comparative_report():
    """Generate a context-aware comparative report with enhanced AI insights"""
    try:
        data = request.get_json()
        if not data:
            raise ApiError("Missing request body")
        
        # Extract configuration
        establishment_id = data.get('establishmentId')
        establishment_name = data.get('establishmentName', 'Unknown School')
        report_type = data.get('reportType')
        config = data.get('config', {})
        filters = data.get('filters', {})
        
        # Extract context fields
        organizational_context = config.get('organizationalContext', '')
        specific_questions = config.get('specificQuestions', '')
        historical_context = config.get('historicalContext', '')
        
        # Extract branding
        establishment_logo_url = config.get('establishmentLogoUrl', '')
        primary_color = config.get('primaryColor', '#667eea')
        
        app.logger.info(f"Generating comparative report for {establishment_name}")
        app.logger.info(f"Report type: {report_type}")
        app.logger.info(f"Has context: {bool(organizational_context)}")
        
        # Fetch comparison data from Supabase
        comparison_data = fetch_comparison_data(
            establishment_id, 
            report_type, 
            config
        )
        
        # Generate AI insights with context
        ai_insights = generate_contextual_insights(
            comparison_data, 
            organizational_context,
            specific_questions,
            historical_context,
            report_type,
            establishment_name
        )
        
        # Create PDF with custom branding
        pdf_buffer = create_branded_pdf(
            establishment_name,
            establishment_logo_url,
            primary_color,
            comparison_data,
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

def fetch_comparison_data(establishment_id, report_type, config):
    """Fetch data from comparative_metrics view"""
    try:
        if report_type == 'cycle_progression':
            cycles = config.get('cycles', [])
            
            # Query comparative_metrics for each cycle
            data = {}
            for cycle in cycles:
                result = supabase.table('comparative_metrics') \
                    .select('*') \
                    .eq('establishment_id', establishment_id) \
                    .eq('cycle', cycle) \
                    .execute()
                
                if result.data:
                    # Calculate aggregates
                    scores = [r['overall'] for r in result.data if r['overall']]
                    data[f'cycle_{cycle}'] = {
                        'mean': np.mean(scores) if scores else 0,
                        'std': np.std(scores) if scores else 0,
                        'count': len(scores),
                        'raw_data': result.data
                    }
            
            return data
            
        elif report_type == 'group_comparison':
            dimension = config.get('groupDimension')
            groups = config.get('groups', [])
            
            data = {}
            for group in groups:
                result = supabase.table('comparative_metrics') \
                    .select('*') \
                    .eq('establishment_id', establishment_id) \
                    .eq(dimension, group) \
                    .execute()
                
                if result.data:
                    scores = [r['overall'] for r in result.data if r['overall']]
                    data[group] = {
                        'mean': np.mean(scores) if scores else 0,
                        'std': np.std(scores) if scores else 0,
                        'count': len(scores),
                        'raw_data': result.data
                    }
            
            return data
            
    except Exception as e:
        app.logger.error(f"Failed to fetch comparison data: {e}")
        return {}

def generate_contextual_insights(comparison_data, org_context, questions, historical, report_type, school_name):
    """Generate AI insights with organizational context"""
    
    if not OPENAI_API_KEY:
        return {
            'summary': 'AI insights not available - API key not configured',
            'key_findings': [],
            'recommendations': []
        }
    
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        
        # Build comprehensive context
        data_summary = summarize_comparison_data(comparison_data)
        
        # Enhanced system prompt with context awareness
        system_prompt = """You are an expert educational data analyst specializing in VESPA metrics and student performance analysis. 
        You provide evidence-based, actionable insights that are specific to the school's context and concerns.
        Focus on practical recommendations that can be implemented immediately.
        When the user provides organizational context, pay special attention to addressing their specific concerns and questions."""
        
        # Build user prompt with all context
        user_prompt = f"""
        School: {school_name}
        Report Type: {report_type}
        
        DATA SUMMARY:
        {data_summary}
        
        ORGANIZATIONAL CONTEXT:
        {org_context if org_context else 'No specific context provided'}
        
        SPECIFIC QUESTIONS TO ADDRESS:
        {questions if questions else 'No specific questions provided'}
        
        HISTORICAL CONTEXT:
        {historical if historical else 'No historical context provided'}
        
        Please provide:
        1. An executive summary (2-3 paragraphs) that directly addresses the organizational context
        2. 3-5 key findings with statistical support
        3. 3-5 specific, actionable recommendations
        4. If questions were provided, ensure each is answered with data-driven insights
        
        Focus especially on:
        - Explaining unexpected patterns (e.g., if Year 13 shows lower confidence than Year 12)
        - Identifying root causes based on the data
        - Providing practical interventions
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4" if "gpt-4" in OPENAI_API_KEY else "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        # Parse the response
        ai_text = response.choices[0].message['content']
        
        # Extract sections (basic parsing - could be enhanced)
        sections = ai_text.split('\n\n')
        
        return {
            'summary': sections[0] if sections else '',
            'key_findings': extract_bullet_points(ai_text, 'findings'),
            'recommendations': extract_bullet_points(ai_text, 'recommendations'),
            'full_analysis': ai_text
        }
        
    except Exception as e:
        app.logger.error(f"AI generation failed: {e}")
        return {
            'summary': 'Unable to generate AI insights',
            'key_findings': [],
            'recommendations': [],
            'error': str(e)
        }

def summarize_comparison_data(data):
    """Create a text summary of comparison data for AI context"""
    summary = []
    
    for key, values in data.items():
        if isinstance(values, dict) and 'mean' in values:
            summary.append(f"{key}: Mean={values['mean']:.2f}, StdDev={values['std']:.2f}, N={values['count']}")
            
            # Add VESPA breakdowns if available
            if 'raw_data' in values and values['raw_data']:
                sample = values['raw_data'][0]
                if 'vision' in sample:
                    vespa_means = {
                        'Vision': np.mean([r['vision'] for r in values['raw_data'] if r.get('vision')]),
                        'Effort': np.mean([r['effort'] for r in values['raw_data'] if r.get('effort')]),
                        'Systems': np.mean([r['systems'] for r in values['raw_data'] if r.get('systems')]),
                        'Practice': np.mean([r['practice'] for r in values['raw_data'] if r.get('practice')]),
                        'Attitude': np.mean([r['attitude'] for r in values['raw_data'] if r.get('attitude')])
                    }
                    summary.append(f"  VESPA breakdown: {vespa_means}")
    
    return '\n'.join(summary)

def extract_bullet_points(text, section_type):
    """Extract bullet points from AI response"""
    lines = text.split('\n')
    bullets = []
    
    for line in lines:
        if line.strip().startswith(('-', '•', '*', '1.', '2.', '3.', '4.', '5.')):
            bullets.append(line.strip().lstrip('-•*0123456789. '))
    
    return bullets[:5]  # Return top 5

def create_branded_pdf(school_name, logo_url, primary_color, data, insights, config):
    """Create a professionally branded PDF report"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.platypus import HRFlowable
    from io import BytesIO
    import requests
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.75*inch)
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom title style with primary color
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor(primary_color),
        spaceAfter=30,
        alignment=1  # Center
    )
    
    # Header with logos
    header_table_data = []
    header_row = []
    
    # Add establishment logo if provided
    if logo_url:
        try:
            response = requests.get(logo_url, timeout=5)
            if response.status_code == 200:
                logo_buffer = BytesIO(response.content)
                establishment_logo = Image(logo_buffer, width=1.5*inch, height=1.5*inch)
                header_row.append(establishment_logo)
            else:
                header_row.append('')
        except:
            header_row.append('')
    else:
        header_row.append('')
    
    # Add title in center
    header_row.append(Paragraph(f"<b>{school_name}</b><br/>Comparative Analysis Report", title_style))
    
    # Add VESPA logo
    try:
        vespa_response = requests.get('https://vespa.academy/_astro/vespalogo.BGrK1ARl.png', timeout=5)
        if vespa_response.status_code == 200:
            vespa_buffer = BytesIO(vespa_response.content)
            vespa_logo = Image(vespa_buffer, width=1.5*inch, height=1.5*inch)
            header_row.append(vespa_logo)
        else:
            header_row.append('')
    except:
        header_row.append('')
    
    header_table_data.append(header_row)
    
    header_table = Table(header_table_data, colWidths=[2*inch, 3.5*inch, 2*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Executive Summary with AI insights
    elements.append(Paragraph("<b>Executive Summary</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(insights.get('summary', 'No summary available'), styles['BodyText']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Key Findings
    if insights.get('key_findings'):
        elements.append(Paragraph("<b>Key Findings</b>", styles['Heading2']))
        for finding in insights['key_findings']:
            elements.append(Paragraph(f"• {finding}", styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))
    
    # Data visualization section would go here
    # (Charts would be generated using matplotlib and added as images)
    
    # Recommendations
    if insights.get('recommendations'):
        elements.append(Paragraph("<b>Recommendations</b>", styles['Heading2']))
        for rec in insights['recommendations']:
            elements.append(Paragraph(f"• {rec}", styles['BodyText']))
        elements.append(Spacer(1, 0.3*inch))
    
    # Footer with context note
    if config.get('organizationalContext'):
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("<i>This report was generated with consideration of the following organizational context:</i>", styles['Normal']))
        elements.append(Paragraph(f"<i>{config['organizationalContext'][:200]}...</i>", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer
