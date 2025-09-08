// ============================================
// VESPA DASHBOARD - ACADEMIC YEAR DEBUG SCRIPT
// ============================================
// Copy and paste this entire script into your browser console
// when the dashboard is loaded

console.log("%c=== VESPA DASHBOARD DEBUG ===", "color: blue; font-size: 16px; font-weight: bold");

// 1. Check Vue app instance
const app = document.querySelector('#app')?.__vue_app__;
if (!app) {
    console.error("❌ Vue app not found. Make sure dashboard is loaded.");
} else {
    console.log("✅ Vue app found");
    
    // 2. Access the Pinia store
    const stores = app._context.provides;
    let dashboardStore = null;
    
    // Find the dashboard store
    for (let key in stores) {
        if (stores[key] && stores[key].filters) {
            dashboardStore = stores[key];
            break;
        }
    }
    
    if (dashboardStore) {
        console.log("✅ Dashboard store found");
        console.log("📊 Current filters:", dashboardStore.filters);
    } else {
        console.log("❌ Dashboard store not found");
    }
}

// 3. Check the academic year dropdown
console.log("\n%c=== CHECKING DROPDOWN ===", "color: green; font-size: 14px; font-weight: bold");

const yearDropdown = document.querySelector('select[class*="form-select"]');
if (yearDropdown) {
    const options = yearDropdown.querySelectorAll('option');
    console.log(`📅 Found ${options.length} options in academic year dropdown:`);
    
    const yearValues = [];
    options.forEach((option, index) => {
        const value = option.value;
        const text = option.textContent.trim();
        yearValues.push({index, value, text});
        console.log(`  ${index}: "${text}" (value: "${value}")`);
    });
    
    // Check for duplicates
    const valueSet = new Set();
    const duplicates = [];
    yearValues.forEach(item => {
        if (valueSet.has(item.value)) {
            duplicates.push(item);
        }
        valueSet.add(item.value);
    });
    
    if (duplicates.length > 0) {
        console.log("%c⚠️ DUPLICATES FOUND:", "color: red; font-weight: bold");
        duplicates.forEach(dup => {
            console.log(`  Duplicate: "${dup.text}" at index ${dup.index}`);
        });
    } else {
        console.log("✅ No duplicate values found");
    }
} else {
    console.log("❌ Academic year dropdown not found");
}

// 4. Intercept API calls to see what's being fetched
console.log("\n%c=== INTERCEPTING API CALLS ===", "color: purple; font-size: 14px; font-weight: bold");
console.log("Monitoring /api/academic-years calls...");

// Store original fetch
const originalFetch = window.fetch;
window.fetch = function(...args) {
    const url = args[0];
    if (url && url.includes('/api/academic-years')) {
        console.log(`📡 API Call to: ${url}`);
        return originalFetch.apply(this, args).then(response => {
            // Clone response to read it
            const cloned = response.clone();
            cloned.json().then(data => {
                console.log(`📥 Academic years received:`, data);
                if (Array.isArray(data)) {
                    console.log(`  Count: ${data.length}`);
                    console.log(`  Values: ${JSON.stringify(data)}`);
                    
                    // Check for duplicates in API response
                    const uniqueYears = [...new Set(data)];
                    if (uniqueYears.length !== data.length) {
                        console.log(`%c⚠️ API returning duplicates!`, "color: red; font-weight: bold");
                        console.log(`  Unique count: ${uniqueYears.length}`);
                        console.log(`  Total count: ${data.length}`);
                    }
                }
            }).catch(e => console.error("Error parsing response:", e));
            return response;
        });
    }
    return originalFetch.apply(this, args);
};

// 5. Check FilterBar component data
console.log("\n%c=== CHECKING FILTERBAR COMPONENT ===", "color: teal; font-size: 14px; font-weight: bold");

// Try to find FilterBar component
const filterBarEl = document.querySelector('.filter-bar');
if (filterBarEl && filterBarEl.__vueParentComponent) {
    const filterBarComponent = filterBarEl.__vueParentComponent;
    console.log("FilterBar component found");
    
    // Try to access the component's data
    if (filterBarComponent.ctx) {
        console.log("FilterBar academicYears data:", filterBarComponent.ctx.academicYears);
    }
} else {
    console.log("FilterBar component not directly accessible");
    console.log("Try refreshing the academic years by changing school to trigger reload");
}

// 6. Manual API test
console.log("\n%c=== MANUAL API TEST ===", "color: orange; font-size: 14px; font-weight: bold");
console.log("Fetching academic years directly...");

// Get the base URL from the page or use default
const baseUrl = window.location.origin;
fetch(`${baseUrl}/api/academic-years`)
    .then(res => res.json())
    .then(data => {
        console.log("📊 Direct API response:", data);
        if (Array.isArray(data)) {
            const uniqueValues = [...new Set(data)];
            console.log(`  Total items: ${data.length}`);
            console.log(`  Unique items: ${uniqueValues.length}`);
            if (data.length !== uniqueValues.length) {
                console.log("%c⚠️ API is returning duplicate years!", "color: red; font-size: 14px; font-weight: bold");
                
                // Count occurrences
                const counts = {};
                data.forEach(year => {
                    counts[year] = (counts[year] || 0) + 1;
                });
                
                console.log("Year counts:");
                Object.entries(counts).forEach(([year, count]) => {
                    if (count > 1) {
                        console.log(`  "${year}": appears ${count} times`);
                    }
                });
            }
        }
    })
    .catch(err => console.error("Error fetching academic years:", err));

console.log("\n%cDebug script loaded. Change schools or refresh to see API calls.", "color: gray; font-style: italic");
console.log("To manually trigger a refresh, you can run: location.reload()");
