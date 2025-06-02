// dashboard.js

// Ensure this matches the initializerFunctionName in WorkingBridge.js
function initializeDashboardApp() {
    // Get the configuration set by WorkingBridge.js
    const config = window.DASHBOARD_CONFIG;
    if (!config) {
        console.error("DASHBOARD_CONFIG not found. Dashboard cannot initialize.");
        return;
    }

    console.log("Initializing Dashboard App with config:", config);
    const {
        knackAppId,
        knackApiKey,
        debugMode,
        sceneKey,
        viewKey,
        elementSelector,
        herokuAppUrl, // Your Heroku backend URL
        objectKeys,
        themeColors
    } = config;

    // --- Helper Functions (General) ---
    function log(message, data) {
        if (debugMode) {
            console.log(`[Dashboard App] ${message}`, data === undefined ? '' : data);
        }
    }

    function errorLog(message, error) {
        console.error(`[Dashboard App ERROR] ${message}`, error);
    }

    // --- Knack API Helper ---
    // You'll need functions to fetch data from Knack.
    // These will typically use your Heroku app as a proxy to securely call the Knack API.
    // Example:
    async function fetchDataFromKnack(objectKey, filters = []) {
        const url = `${herokuAppUrl}/api/knack-data?objectKey=${objectKey}&filters=${encodeURIComponent(JSON.stringify(filters))}`;
        // Add appropriate headers if your Heroku app requires them (e.g., API key for your Heroku app itself)
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Knack API request failed with status ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            errorLog(`Failed to fetch data for ${objectKey}`, error);
            throw error; // Re-throw to be handled by the caller
        }
    }

    // --- UI Rendering ---
    function renderDashboardUI(container) {
        log("Rendering Dashboard UI into:", container);
        container.innerHTML = `
            <div id="dashboard-container">
                <header>
                    <h1>VESPA Performance Dashboard</h1>
                </header>
                <section id="overview-section">
                    <h2>School Overview & Benchmarking</h2>
                    <div id="averages-chart-container"></div>
                    <div id="distribution-charts-container">
                        <!-- Containers for Vision, Effort, Systems, Practice, Attitude -->
                    </div>
                </section>
                <section id="qla-section">
                    <h2>Question Level Analysis</h2>
                    <div id="qla-controls">
                        <select id="qla-question-dropdown"></select>
                        <input type="text" id="qla-chat-input" placeholder="Ask about the question data...">
                        <button id="qla-chat-submit">Ask AI</button>
                    </div>
                    <div id="qla-ai-response"></div>
                    <div id="qla-top-bottom-questions">
                        <h3>Top 5 Questions</h3>
                        <ul id="qla-top-5"></ul>
                        <h3>Bottom 5 Questions</h3>
                        <ul id="qla-bottom-5"></ul>
                    </div>
                    <div id="qla-stats">
                        <!-- Other interesting statistical info -->
                    </div>
                </section>
                <section id="student-insights-section">
                    <h2>Student Comment Insights</h2>
                    <div id="word-cloud-container"></div>
                    <div id="common-themes-container"></div>
                </section>
            </div>
        `;
        // Add event listeners for UI elements (e.g., qla-chat-submit)
        document.getElementById('qla-chat-submit').addEventListener('click', handleQLAChatSubmit);
    }

    // --- Section 1: Overview and Benchmarking ---
    async function loadOverviewData() {
        log("Loading overview data...");
        try {
            // 1. Fetch all VESPA Results (object_10) for the logged-in user's customer group
            //    This requires knowing how to filter by "Customer". You might need another call
            //    to get the current user's details first, or pass customer ID in config.
            //    For now, assuming you can filter directly or get all and filter client-side (less ideal for large datasets).
            const allVespaResults = await fetchDataFromKnack(objectKeys.vespaResults); // May need filters

            // 2. Fetch *ALL* data for national benchmarking (if your Heroku app can provide this)
            //    Alternatively, your Heroku app could pre-calculate national averages.
            const nationalBenchmarkData = {}; // Placeholder - this needs to come from somewhere

            // 3. Calculate Averages for User's School
            const schoolAverages = calculateVespaAverages(allVespaResults, 'current'); // 'current' uses field_146 to get latest
            log("School Averages:", schoolAverages);

            // 4. Render Averages Comparison Chart (e.g., using Chart.js or similar)
            renderAveragesChart(schoolAverages, nationalBenchmarkData);

            // 5. Calculate and Render Distribution Charts for each component
            renderDistributionCharts(allVespaResults, themeColors);

        } catch (error) {
            errorLog("Failed to load overview data", error);
            // Display error to user in the UI
        }
    }

    function calculateVespaAverages(results, cycleType = 'current') {
        // results: array of records from object_10
        // cycleType: 'current', 'cycle1', 'cycle2', 'cycle3'
        const averages = { vision: 0, effort: 0, systems: 0, practice: 0, attitude: 0, overall: 0 };
        let count = 0;
        if (!results || results.length === 0) return averages;

        results.forEach(record => {
            let v, e, s, p, a, o;
            const currentMCycle = record.field_146_raw; // Assuming this is the numeric cycle number

            if (cycleType === 'current' && currentMCycle) {
                v = parseFloat(record[`field_${146 + currentMCycle}_raw`]); // e.g., field_147_raw if currentMCycle is 1 (Vision)
                e = parseFloat(record[`field_${147 + currentMCycle}_raw`]);
                s = parseFloat(record[`field_${148 + currentMCycle}_raw`]);
                p = parseFloat(record[`field_${149 + currentMCycle}_raw`]);
                a = parseFloat(record[`field_${150 + currentMCycle}_raw`]);
                o = parseFloat(record[`field_${151 + currentMCycle}_raw`]);
             } else if (cycleType === 'cycle1') {
                v = parseFloat(record.field_155_raw); e = parseFloat(record.field_156_raw);
                s = parseFloat(record.field_157_raw); p = parseFloat(record.field_158_raw);
                a = parseFloat(record.field_159_raw); o = parseFloat(record.field_160_raw);
            } // ... add for cycle2 and cycle3 similarly based on README
             else { // Fallback or if cycleType is specific and currentMCycle doesn't match
                v = parseFloat(record.field_147_raw); e = parseFloat(record.field_148_raw);
                s = parseFloat(record.field_149_raw); p = parseFloat(record.field_150_raw);
                a = parseFloat(record.field_151_raw); o = parseFloat(record.field_152_raw);
            }


            if (!isNaN(v)) { averages.vision += v; }
            if (!isNaN(e)) { averages.effort += e; }
            if (!isNaN(s)) { averages.systems += s; }
            if (!isNaN(p)) { averages.practice += p; }
            if (!isNaN(a)) { averages.attitude += a; }
            if (!isNaN(o)) { averages.overall += o; count++;} // Assuming overall score presence means valid record
        });

        if (count > 0) {
            for (const key in averages) {
                averages[key] = parseFloat((averages[key] / count).toFixed(2));
            }
        }
        return averages;
    }

    function renderAveragesChart(schoolData, nationalData) {
        const container = document.getElementById('averages-chart-container');
        if (!container) return;
        log("Rendering averages chart with School:", schoolData, "National:", nationalData);
        // Use a charting library like Chart.js, D3, etc.
        // Example: container.innerHTML = `<p>School Vision: ${schoolData.vision}, National Vision: ${nationalData.vision || 'N/A'}</p>`;
        // You'll want a bar chart comparing school vs national for V, E, S, P, A.
    }

    function renderDistributionCharts(results, colors) {
        const container = document.getElementById('distribution-charts-container');
        if (!container) return;
        log("Rendering distribution charts.");
        // For each component (Vision, Effort, etc.):
        // 1. Extract all scores for that component from results.
        // 2. Create a histogram/distribution (e.g., how many students scored 1, 2, ..., 10).
        // 3. Render using a charting library. Apply themeColors.
        // Example:
        // const visionScores = results.map(r => parseFloat(r.field_147_raw)).filter(s => !isNaN(s));
        // const effortScores = results.map(r => parseFloat(r.field_148_raw)).filter(s => !isNaN(s));
        // ... and so on for all components
        // Then render a chart for each set of scores.
        container.innerHTML = "<p>Distribution charts will go here.</p>";
    }


    // --- Section 2: Question Level Analysis (QLA) ---
    let allQuestionResponses = []; // Cache for QLA data

    async function loadQLAData() {
        log("Loading QLA data...");
        try {
            // Fetch all records from Object_29 (Questionnaire Qs)
            // Again, filtering by customer/school might be needed via Heroku.
            allQuestionResponses = await fetchDataFromKnack(objectKeys.questionnaireResponses);
            log("QLA data loaded:", allQuestionResponses.length, "responses");

            // Populate dropdown with questions from the text file.
            // Your Heroku app could serve the question list, or you can embed a summarized version.
            populateQLAQuestionDropdown();

            // Calculate and display Top 5 / Bottom 5 questions
            displayTopBottomQuestions(allQuestionResponses);

            // Display other stats
            displayQLAStats(allQuestionResponses);

        } catch (error) {
            errorLog("Failed to load QLA data", error);
        }
    }
    
    async function getQuestionTextMapping() {
        // In a real app, this might come from a JSON file served by your Heroku app
        // or could be fetched from another Knack object if you store it there.
        // For now, returning a placeholder.
        // This mapping is crucial for making sense of field_XXX to actual question text.
        // Refer to your AIVESPACoach/question_id_to_text_mapping.json and AIVESPACoach/psychometric_question_details.json
        return {
            // Example: 'field_794': "I have a clear vision for my future.",
            // ... populate this extensively based on your JSON files
        };
    }


    async function populateQLAQuestionDropdown() {
        const dropdown = document.getElementById('qla-question-dropdown');
        if (!dropdown) return;

        // Fetch questions from your "Question Level Analysis - Interrogation Questions.txt"
        // This could be done by having your Heroku app serve this file's content as JSON
        // or by pre-processing it.
        try {
            const response = await fetch(`${herokuAppUrl}/api/interrogation-questions`); // Endpoint on your Heroku app
            if (!response.ok) throw new Error('Failed to fetch interrogation questions');
            const questions = await response.json(); // Assuming Heroku serves it as JSON array

            questions.forEach(q => {
                const option = document.createElement('option');
                option.value = q; // Or an ID if you have one
                option.textContent = q;
                dropdown.appendChild(option);
            });
            log("Populated QLA question dropdown.");
        } catch (error) {
            errorLog("Failed to populate QLA question dropdown", error);
            dropdown.innerHTML = "<option>Error loading questions</option>";
        }
    }
    
    function calculateAverageScoresForQuestions(responses) {
        const questionScores = {};
        const questionCounts = {};
        const questionFieldToText = getQuestionTextMapping(); // You'll need this mapping

        responses.forEach(record => {
            // Iterate over fields that represent question answers (field_794 - field_821, etc.)
            // This needs to align with your Object_29 structure and question_id_to_text_mapping.json
            for (const fieldKey in record) {
                if (fieldKey.startsWith('field_') && fieldKey.endsWith('_raw')) { // Generic way to find potential question fields
                    const questionId = fieldKey.replace('_raw', ''); // e.g., field_794
                    // Check if this field is actually a question field you care about
                    // based on question_id_to_text_mapping.json or psychometric_question_details.json
                    if (questionFieldToText[questionId]) { // Or some other validation
                        const score = parseInt(record[fieldKey], 10);
                        if (!isNaN(score)) {
                            questionScores[questionId] = (questionScores[questionId] || 0) + score;
                            questionCounts[questionId] = (questionCounts[questionId] || 0) + 1;
                        }
                    }
                }
            }
        });

        const averageScores = {};
        for (const qId in questionScores) {
            averageScores[qId] = parseFloat((questionScores[qId] / questionCounts[qId]).toFixed(2));
        }
        return averageScores; // { field_XXX: average_score, ... }
    }

    async function displayTopBottomQuestions(responses) {
        if (!responses || responses.length === 0) return;
        
        const averageScores = calculateAverageScoresForQuestions(responses);
        const questionTextMapping = await getQuestionTextMapping();

        const sortedQuestions = Object.entries(averageScores)
            .map(([fieldId, avgScore]) => ({
                id: fieldId,
                text: questionTextMapping[fieldId] || `Unknown Question (${fieldId})`,
                score: avgScore
            }))
            .sort((a, b) => b.score - a.score);

        const top5 = sortedQuestions.slice(0, 5);
        const bottom5 = sortedQuestions.slice(-5).reverse(); // Reverse to show lowest score first if desired

        const top5ul = document.getElementById('qla-top-5');
        const bottom5ul = document.getElementById('qla-bottom-5');

        if (top5ul) {
            top5ul.innerHTML = top5.map(q => `<li>${q.text} (Avg: ${q.score})</li>`).join('');
        }
        if (bottom5ul) {
            bottom5ul.innerHTML = bottom5.map(q => `<li>${q.text} (Avg: ${q.score})</li>`).join('');
        }
        log("Displayed Top/Bottom 5 questions.");
    }


    function displayQLAStats(responses) {
        // Calculate and display other stats:
        // - Overall response distribution for key questions
        // - Percentage agreement/disagreement for certain statements
        const statsContainer = document.getElementById('qla-stats');
        if (statsContainer) {
            statsContainer.innerHTML = "<p>Other QLA stats will go here.</p>";
        }
    }

    async function handleQLAChatSubmit() {
        const inputElement = document.getElementById('qla-chat-input');
        const dropdownElement = document.getElementById('qla-question-dropdown');
        const responseContainer = document.getElementById('qla-ai-response');

        if (!inputElement || !dropdownElement || !responseContainer) return;

        const userQuery = inputElement.value.trim();
        const selectedQuestion = dropdownElement.value;
        let queryForAI = userQuery;

        if (!queryForAI && selectedQuestion) {
            queryForAI = selectedQuestion; // Use dropdown question if input is empty
        }

        if (!queryForAI) {
            responseContainer.textContent = "Please type a question or select one from the dropdown.";
            return;
        }

        responseContainer.textContent = "Thinking...";
        log("Sending QLA query to AI:", queryForAI);

        try {
            // This is where you'd make a call to your Heroku backend
            // The backend would then use the OpenAI API with the relevant question data context.
            const aiResponse = await fetch(`${herokuAppUrl}/api/qla-chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // Send the query AND relevant context (e.g., data for the specific question or all QLA data)
                // Your Heroku app will need to be smart about how it uses this data with the OpenAI prompt.
                body: JSON.stringify({ query: queryForAI, questionData: allQuestionResponses /* or more filtered data */ })
            });

            if (!aiResponse.ok) {
                const errorData = await aiResponse.json();
                throw new Error(errorData.message || `AI request failed with status ${aiResponse.status}`);
            }

            const result = await aiResponse.json();
            responseContainer.textContent = result.answer; // Assuming your Heroku app returns { answer: "..." }
            log("AI Response for QLA:", result.answer);

        } catch (error) {
            errorLog("Error with QLA AI chat:", error);
            responseContainer.textContent = `Error: ${error.message}`;
        }
    }


    // --- Section 3: Student Comment Insights ---
    async function loadStudentCommentInsights() {
        log("Loading student comment insights...");
        try {
            // Fetch VESPA Results (object_10) which contains comment fields
            const vespaResults = await fetchDataFromKnack(objectKeys.vespaResults);

            // Extract comments (RRC1, RRC2, RRC3, GOAL1, GOAL2, GOAL3 from README)
            const allComments = [];
            vespaResults.forEach(record => {
                if (record.field_2302_raw) allComments.push(record.field_2302_raw); // RRC1
                if (record.field_2303_raw) allComments.push(record.field_2303_raw); // RRC2
                if (record.field_2304_raw) allComments.push(record.field_2304_raw); // RRC3
                if (record.field_2499_raw) allComments.push(record.field_2499_raw); // GOAL1
                if (record.field_2493_raw) allComments.push(record.field_2493_raw); // GOAL2
                if (record.field_2494_raw) allComments.push(record.field_2494_raw); // GOAL3
            });

            log("Total comments extracted:", allComments.length);

            // Render Word Cloud
            renderWordCloud(allComments);

            // Identify and Display Common Themes (this is more complex, might need NLP on Heroku)
            identifyCommonThemes(allComments);

        } catch (error) {
            errorLog("Failed to load student comment insights", error);
        }
    }

    function renderWordCloud(comments) {
        const container = document.getElementById('word-cloud-container');
        if (!container) return;
        log("Rendering word cloud.");
        // Use a library like WordCloud.js (https://wordcloud2.js.org/) or similar.
        // You'll need to process the text: concatenate, remove stop words, count frequencies.
        // Example (conceptual):
        // const textBlob = comments.join(" ");
        // const wordFrequencies = calculateWordFrequencies(textBlob);
        // WordCloud(container, { list: wordFrequencies });
        container.innerHTML = "<p>Word cloud will go here.</p>";

    }

    function identifyCommonThemes(comments) {
        const container = document.getElementById('common-themes-container');
        if (!container) return;
        log("Identifying common themes.");
        // This is a more advanced NLP task.
        // Simplistic: Count occurrences of keywords.
        // Advanced: Use your Heroku backend + OpenAI to summarize themes.
        // Example:
        // Send comments to Heroku -> Heroku uses OpenAI to extract themes -> display themes.
        container.innerHTML = "<p>Common themes will be listed here.</p>";
    }

    // --- Initialization ---
    const targetElement = document.querySelector(elementSelector);
    if (targetElement) {
        renderDashboardUI(targetElement);
        // Load data for each section
        loadOverviewData();
        loadQLAData();
        loadStudentCommentInsights();
    } else {
        errorLog(`Target element "${elementSelector}" not found for dashboard.`);
    }
}

// Defensive check: If jQuery is used by Knack/other scripts, ensure this script runs after.
// However, the loader script (WorkingBridge.js) should handle calling initializeDashboardApp
// at the appropriate time.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // initializeDashboardApp(); // Not strictly necessary if WorkingBridge calls it
    });
} else {
    // initializeDashboardApp(); // Or call if DOM is already ready, though WorkingBridge is preferred.
}
