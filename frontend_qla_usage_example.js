// Example: How to use pre-calculated QLA statistics from Supabase in the frontend

// Instead of calculating statistics client-side, fetch pre-calculated data
async function loadQLADataOptimized(establishmentId, cycle = 1, filters = {}) {
    try {
        // 1. Get top/bottom questions directly from the view
        const { data: topBottomQuestions, error } = await supabase
            .rpc('get_qla_top_bottom_questions', {
                p_establishment_id: establishmentId,
                p_cycle: cycle
            });

        if (error) throw error;

        // Separate top 5 and bottom 5
        const top5 = topBottomQuestions
            .filter(q => q.performance_category === 'TOP_5')
            .slice(0, 5);
        
        const bottom5 = topBottomQuestions
            .filter(q => q.performance_category === 'BOTTOM_5')
            .slice(0, 5);

        // 2. If filters are applied, use the dynamic calculation function
        if (filters.yearGroup || filters.faculty || filters.group) {
            const { data: filteredStats, error: filterError } = await supabase
                .rpc('get_qla_statistics', {
                    p_establishment_id: establishmentId,
                    p_cycle: cycle,
                    p_year_group: filters.yearGroup,
                    p_faculty: filters.faculty,
                    p_group: filters.group
                });

            if (filterError) throw filterError;

            // Process filtered results
            return processQLAResults(filteredStats);
        }

        // 3. For unfiltered data, use the pre-calculated view
        const { data: allQuestionStats, error: statsError } = await supabase
            .from('qla_question_performance')
            .select('*')
            .eq('establishment_id', establishmentId)
            .eq('cycle', cycle);

        if (statsError) throw statsError;

        return {
            top5Questions: top5,
            bottom5Questions: bottom5,
            allQuestionStats: allQuestionStats,
            summary: {
                totalQuestions: allQuestionStats.length,
                averageMean: calculateAverage(allQuestionStats.map(q => q.mean)),
                questionsAboveNational: allQuestionStats.filter(q => q.diff_from_national > 0).length,
                questionsBelowNational: allQuestionStats.filter(q => q.diff_from_national < 0).length
            }
        };

    } catch (error) {
        console.error('Error loading QLA data:', error);
        throw error;
    }
}

// Replace the calculateAverageScoresForQuestions function
function displayTopBottomQuestionsOptimized(topBottomData, questionTextMapping) {
    // No need to calculate - data already comes with top 5 and bottom 5
    const { top5Questions, bottom5Questions } = topBottomData;

    // Map question IDs to text
    const enrichedTop5 = top5Questions.map(q => ({
        id: q.question_id,
        text: questionTextMapping[q.question_id] || `Question ${q.question_id}`,
        score: q.mean,
        stdDev: q.std_dev,
        responseCount: q.count,
        mode: q.mode,
        distribution: q.distribution,
        nationalMean: q.national_mean,
        diffFromNational: q.diff_from_national
    }));

    const enrichedBottom5 = bottom5Questions.map(q => ({
        id: q.question_id,
        text: questionTextMapping[q.question_id] || `Question ${q.question_id}`,
        score: q.mean,
        stdDev: q.std_dev,
        responseCount: q.count,
        mode: q.mode,
        distribution: q.distribution,
        nationalMean: q.national_mean,
        diffFromNational: q.diff_from_national
    }));

    // Render the cards
    renderEnhancedQuestionCards(enrichedTop5, enrichedBottom5);
}

// The calculateQuestionStatistics function can be simplified
function getQuestionStatisticsOptimized(questionId, preCalculatedStats) {
    // Find the pre-calculated stats for this question
    const stats = preCalculatedStats.find(q => q.question_id === questionId);
    
    if (stats) {
        return {
            count: stats.count,
            stdDev: stats.std_dev,
            mode: stats.mode,
            distribution: stats.distribution,
            mean: stats.mean,
            percentile25: stats.percentile_25,
            percentile75: stats.percentile_75,
            nationalMean: stats.national_mean,
            diffFromNational: stats.diff_from_national
        };
    }
    
    // Fallback if not found
    return {
        count: 0,
        stdDev: 0,
        mode: 0,
        distribution: [0, 0, 0, 0, 0],
        mean: 0
    };
}

// Example of how to integrate with existing dashboard
async function initializeQLASection(establishmentId, cycle, filters) {
    try {
        // Show loading state
        showQLALoading();

        // Load pre-calculated data
        const qlaData = await loadQLADataOptimized(establishmentId, cycle, filters);
        
        // Get question text mapping (this can also be cached)
        const questionTextMapping = await getQuestionTextMapping();

        // Display top/bottom questions using pre-calculated data
        displayTopBottomQuestionsOptimized(qlaData, questionTextMapping);

        // Hide loading state
        hideQLALoading();

    } catch (error) {
        console.error('Failed to initialize QLA section:', error);
        showQLAError();
    }
}