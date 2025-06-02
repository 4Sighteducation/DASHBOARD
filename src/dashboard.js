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
        const url = `${config.herokuAppUrl}/api/knack-data?objectKey=${objectKey}&filters=${encodeURIComponent(JSON.stringify(filters))}`;
        log("Fetching from backend URL:", url); // Added for debugging
        // Add appropriate headers if your Heroku app requires them (e.g., API key for your Heroku app itself)
        try {
            const response = await fetch(url);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: `Knack API request via backend failed with status ${response.status}` }));
                throw new Error(errorData.message || `Knack API request via backend failed with status ${response.status}`);
            }
            const data = await response.json();
            return data.records; // The backend now wraps records in a 'records' key
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
            // 1. Fetch VESPA Results for the logged-in user's Staff Admin group (User School Data)
            let schoolVespaResults = [];
            if (config.loggedInUserStaffAdminId) { // Ensure this ID is passed in DASHBOARD_CONFIG
                const staffAdminFilter = [{
                    field: 'field_439', // field_439 in object_10 connects to Staff Admin (object_5)
                    operator: 'is',
                    value: config.loggedInUserStaffAdminId
                }];
                schoolVespaResults = await fetchDataFromKnack(config.objectKeys.vespaResults, staffAdminFilter);
                log("Fetched School VESPA Results (filtered by Staff Admin ID):");
            } else {
                log("No Staff Admin ID (loggedInUserStaffAdminId) found in config. Cannot filter school-specific data for overview.");
                // Fetch all if no specific filtering is possible, or show an error.
                // For now, we expect a staff admin ID to correctly scope the data.
            }

            // 2. Fetch *ALL* data for national benchmarking (all entries in object_10)
            const allVespaResultsForBenchmark = await fetchDataFromKnack(config.objectKeys.vespaResults);
            log("Fetched All VESPA Results for Benchmark:", allVespaResultsForBenchmark.length);


            // 3. Calculate Averages for User's School
            const schoolAverages = calculateVespaAverages(schoolVespaResults);
            log("School Averages:", schoolAverages);

            // 4. Calculate Averages for ALL Data (Benchmark)
            const nationalAverages = calculateVespaAverages(allVespaResultsForBenchmark);
            log("National Averages (Benchmark):", nationalAverages);

            // 5. Render Averages Comparison Chart
            renderAveragesChart(schoolAverages, nationalAverages);

            // 6. Calculate and Render Distribution Charts for each component (using school data)
            renderDistributionCharts(schoolVespaResults, config.themeColors);

        } catch (error) {
            errorLog("Failed to load overview data", error);
            // Display error to user in the UI
            const overviewSection = document.getElementById('overview-section');
            if(overviewSection) overviewSection.innerHTML = "<p>Error loading overview data. Please check console.</p>";
        }
    }

    function calculateVespaAverages(results) {
        const averages = { vision: 0, effort: 0, systems: 0, practice: 0, attitude: 0, overall: 0 };
        let validRecordsCount = 0;

        if (!Array.isArray(results) || results.length === 0) {
            log("calculateVespaAverages: Input is not a valid array or is empty", results);
            return averages; // Return default averages if no valid results
        }

        results.forEach(record => {
            // Current VESPA scores are in field_147 to field_152 as per README
            const v = parseFloat(record.field_147_raw);
            const e = parseFloat(record.field_148_raw);
            const s = parseFloat(record.field_149_raw);
            const p = parseFloat(record.field_150_raw);
            const a = parseFloat(record.field_151_raw);
            const o = parseFloat(record.field_152_raw);

            // Check if overall score is a valid number to consider the record
            if (!isNaN(o)) {
                if (!isNaN(v)) averages.vision += v;
                if (!isNaN(e)) averages.effort += e;
                if (!isNaN(s)) averages.systems += s;
                if (!isNaN(p)) averages.practice += p;
                if (!isNaN(a)) averages.attitude += a;
                averages.overall += o; // Already checked o for NaN
                validRecordsCount++;
            }
        });

        if (validRecordsCount > 0) {
            for (const key in averages) {
                averages[key] = parseFloat((averages[key] / validRecordsCount).toFixed(2));
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
    let questionMappings = { id_to_text: {}, psychometric_details: {} }; // Cache for mappings

    async function loadQLAData() {
        log("Loading QLA data...");
        try {
            // Fetch question mappings first
            try {
                const mappingResponse = await fetch(`${config.herokuAppUrl}/api/question-mappings`);
                if (!mappingResponse.ok) {
                    const errorData = await mappingResponse.json().catch(() => ({}));
                    throw new Error(errorData.message || `Failed to fetch question mappings: ${mappingResponse.status}`);
                }
                questionMappings = await mappingResponse.json();
                log("Question mappings loaded:", questionMappings);
            } catch (mapError) {
                errorLog("Failed to load question mappings", mapError);
                // Proceeding without mappings might make QLA less user-friendly
                // but some parts might still work if IDs are used.
            }


            // Fetch all records from Object_29 (Questionnaire Qs)
            // Filter by the logged-in Staff Admin ID
            let qlaFilters = [];
            if (config.loggedInUserStaffAdminId) {
                 // field_2069 in object_29 connects to Staff Admin (object_5) - this is an array connection
                qlaFilters.push({
                    field: 'field_2069', 
                    operator: 'is', // For array connections, 'is' often works like 'contains this ID' in Knack.
                                   // If specific 'is_any_of' or 'contains' is needed and not working, backend might need adjustment.
                    value: config.loggedInUserStaffAdminId
                });
                 allQuestionResponses = await fetchDataFromKnack(config.objectKeys.questionnaireResponses, qlaFilters);
                 log("Fetched QLA Responses (filtered by Staff Admin ID):");
            } else {
                log("No Staff Admin ID (loggedInUserStaffAdminId) found in config. Cannot filter QLA data.");
                // Fetch all if no specific filtering is possible, or show an error.
            }
            // log("QLA data loaded:", allQuestionResponses.length, "responses"); // Already logged above if filtered

            populateQLAQuestionDropdown();
            displayTopBottomQuestions(allQuestionResponses);
            displayQLAStats(allQuestionResponses);

        } catch (error) {
            errorLog("Failed to load QLA data", error);
            const qlaSection = document.getElementById('qla-section');
            if(qlaSection) qlaSection.innerHTML = "<p>Error loading Question Level Analysis data. Please check console.</p>";
        }
    }
    
    async function getQuestionTextMapping() {
        // Now uses the ached mappings from the backend
        return questionMappings.id_to_text || {};
    }


    async function populateQLAQuestionDropdown() {
        const dropdown = document.getElementById('qla-question-dropdown');
        if (!dropdown) return;

        try {
            const response = await fetch(`${config.herokuAppUrl}/api/interrogation-questions`); 
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Failed to fetch interrogation questions');
            }
            const questions = await response.json(); 

            dropdown.innerHTML = '<option value="">Select a question...</option>'; // Clear previous/add default
            questions.forEach(qObj => { // Assuming backend sends array of {id, question}
                const option = document.createElement('option');
                option.value = qObj.question; // Use the question text itself as value, or qObj.id if you prefer
                option.textContent = qObj.question;
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
        const currentQuestionTextMapping = questionMappings.id_to_text || {};

        if (!Array.isArray(responses) || responses.length === 0) {
            log("calculateAverageScoresForQuestions: Input is not a valid array or is empty", responses);
            return {}; // Return empty object if no valid responses
        }

        responses.forEach(record => {
            for (const fieldKeyInRecord in record) {
                // fieldKeyInRecord is like 'field_794_raw'
                if (fieldKeyInRecord.startsWith('field_') && fieldKeyInRecord.endsWith('_raw')) {
                    const baseFieldId = fieldKeyInRecord.replace('_raw', ''); // e.g., field_794
                    
                    // Check if this field is a known question from our mapping
                    if (currentQuestionTextMapping[baseFieldId] || (questionMappings.psychometric_details && isFieldInPsychometricDetails(baseFieldId, questionMappings.psychometric_details))) {
                        const score = parseInt(record[fieldKeyInRecord], 10);
                        if (!isNaN(score) && score >= 1 && score <= 5) { // Assuming 1-5 scale from README for Object_29
                            questionScores[baseFieldId] = (questionScores[baseFieldId] || 0) + score;
                            questionCounts[baseFieldId] = (questionCounts[baseFieldId] || 0) + 1;
                        }
                    }
                }
            }
        });

        const averageScores = {};
        for (const qId in questionScores) {
            if (questionCounts[qId] > 0) {
                averageScores[qId] = parseFloat((questionScores[qId] / questionCounts[qId]).toFixed(2));
            }
        }
        return averageScores; 
    }

    // Helper to check if a fieldId is part of the psychometric question details
    function isFieldInPsychometricDetails(fieldId, psychometricDetailsArray) {
        if (!psychometricDetailsArray || !Array.isArray(psychometricDetailsArray)) return false;
        // psychometric_question_details.json is an array of objects,
        // each object has a 'currentCycleFieldId' property.
        return psychometricDetailsArray.some(qDetail => qDetail.currentCycleFieldId === fieldId);
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
            const aiResponse = await fetch(`${config.herokuAppUrl}/api/qla-chat`, {
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
            let vespaResults = []; // Initialize as empty array
            if (config.loggedInUserStaffAdminId) {
                const staffAdminFilter = [{
                    field: 'field_439', 
                    operator: 'is',
                    value: config.loggedInUserStaffAdminId
                }];
                vespaResults = await fetchDataFromKnack(config.objectKeys.vespaResults, staffAdminFilter);
                log("Fetched VESPA Results for comments (filtered by Staff Admin ID):");
            } else {
                 log("No Staff Admin ID (loggedInUserStaffAdminId) found in config. Cannot filter comments.");
            }
            
            if (!Array.isArray(vespaResults)) {
                errorLog("loadStudentCommentInsights: vespaResults is not an array after fetch.", vespaResults);
                vespaResults = []; // Ensure it's an array to prevent further errors
            }

            const allComments = [];
            if (vespaResults.length > 0) { // Only proceed if we have results
                vespaResults.forEach(record => {
                    if (record.field_2302_raw) allComments.push(record.field_2302_raw); // RRC1
                    if (record.field_2303_raw) allComments.push(record.field_2303_raw); // RRC2
                    if (record.field_2304_raw) allComments.push(record.field_2304_raw); // RRC3
                    if (record.field_2499_raw) allComments.push(record.field_2499_raw); // GOAL1
                    if (record.field_2493_raw) allComments.push(record.field_2493_raw); // GOAL2
                    if (record.field_2494_raw) allComments.push(record.field_2494_raw); // GOAL3
                });
            }

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

// Make sure initializeDashboardApp is globally accessible if WorkingBridge.js calls it.
// If it's not already, you might need:
// window.initializeDashboardApp = initializeDashboardApp;
// However, since it's a top-level function in the script, it should be.
