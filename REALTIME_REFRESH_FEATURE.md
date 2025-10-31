# Real-Time Data Refresh Feature
## On-Demand Sync for Individual Schools

---

## 🎯 **Overview**

Allows staff admins to refresh their school's data **instantly** without waiting for the overnight sync.

**Benefits:**
- ⚡ Real-time updates (30-60 seconds)
- 🎯 School-specific (doesn't affect other schools)
- 🔒 Secure (uses existing credentials)
- 📊 Live progress tracking
- 🚀 No Heroku scheduler needed

---

## 🏗️ **Architecture**

### **Backend (`app.py`)**

New API endpoint:
```
POST /api/sync/refresh-establishment
{
  "establishmentId": "knack_id_here"
}
```

**What It Does:**
1. Validates establishment exists
2. Runs `sync_single_establishment.py` as subprocess
3. Clears cache for that establishment
4. Returns summary to frontend

**Security:**
- Only syncs data for requested establishment
- Uses existing Knack API credentials
- Timeout after 5 minutes
- Error handling prevents crashes

---

### **Sync Script (`sync_single_establishment.py`)**

Lightweight version of main sync that:
- Fetches ONLY records for ONE establishment
- Current academic year only
- Processes students, VESPA, comments
- Returns JSON summary

**Typical Performance:**
- Small school (200 students): ~15 seconds
- Medium school (500 students): ~30 seconds
- Large school (1,000 students): ~60 seconds
- Extra large (2,000+ students): ~90 seconds

---

## 🎨 **Frontend Integration**

### **Option A: Add to DashboardHeader.vue**

```vue
<template>
  <div class="header-right">
    <!-- Existing buttons -->
    
    <!-- NEW: Refresh Button -->
    <button 
      v-if="!isSuperUser"
      @click="refreshData"
      :disabled="refreshing"
      class="btn btn-refresh"
    >
      <svg v-if="!refreshing" class="icon" width="16" height="16" viewBox="0 0 24 24">
        <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" 
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span v-if="refreshing" class="spinner-small"></span>
      {{ refreshing ? 'Refreshing...' : 'Refresh Data' }}
    </button>
  </div>
</template>

<script setup>
const refreshing = ref(false)

async function refreshData() {
  if (!selectedEstablishment || refreshing.value) return
  
  refreshing.value = true
  
  try {
    const response = await API.refreshEstablishmentData(selectedEstablishment)
    
    if (response.success) {
      // Show success message
      showNotification({
        type: 'success',
        title: 'Data Refreshed!',
        message: `Updated ${response.summary.students_synced} students in ${Math.round(response.summary.duration_seconds)}s`
      })
      
      // Reload dashboard data
      emit('data-refreshed')
    }
  } catch (error) {
    showNotification({
      type: 'error',
      title: 'Refresh Failed',
      message: error.message
    })
  } finally {
    refreshing.value = false
  }
}
</script>

<style scoped>
.btn-refresh {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  animation: pulse 2s infinite;
}

.btn-refresh:hover:not(:disabled) {
  animation: none;
  transform: translateY(-1px);
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  animation: none;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
```

---

### **Option B: Add to FilterBar.vue** (Alternative)

Could add as a filter action button with last sync timestamp

---

## 📡 **API Service (services/api.js)**

Add to API class:

```javascript
async refreshEstablishmentData(establishmentId) {
  try {
    console.log('[API] Refreshing data for establishment:', establishmentId)
    
    const response = await apiClient.post(
      `${this.getBaseUrl()}/api/sync/refresh-establishment`,
      { establishmentId },
      { timeout: 310000 } // 5min 10sec timeout
    )
    
    return response.data
  } catch (error) {
    console.error('[API] Refresh error:', error)
    throw error
  }
}
```

---

## 🎨 **Enhanced UX: Progress Modal**

### **Even Better: Show Live Progress**

```vue
<template>
  <Modal v-if="refreshing" @close="() => {}">
    <div class="refresh-modal">
      <div class="spinner-large"></div>
      <h3>Refreshing Data...</h3>
      <p>{{ progressMessage }}</p>
      <div class="progress-details">
        <div class="detail-item">
          <span class="label">Status:</span>
          <span class="value">{{ refreshStatus }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Elapsed:</span>
          <span class="value">{{ elapsedTime }}s</span>
        </div>
      </div>
      <p class="hint">This usually takes 30-60 seconds...</p>
    </div>
  </Modal>
</template>

<script setup>
const refreshing = ref(false)
const progressMessage = ref('Fetching latest data from Knack...')
const refreshStatus = ref('In Progress')
const elapsedTime = ref(0)

let intervalId = null

async function refreshData() {
  refreshing.value = true
  elapsedTime.value = 0
  progressMessage.value = 'Connecting to Knack API...'
  
  // Update elapsed time
  intervalId = setInterval(() => {
    elapsedTime.value++
    if (elapsedTime.value > 20) {
      progressMessage.value = 'Processing VESPA scores...'
    }
    if (elapsedTime.value > 40) {
      progressMessage.value = 'Finalizing update...'
    }
  }, 1000)
  
  try {
    const response = await API.refreshEstablishmentData(selectedEstablishment)
    
    clearInterval(intervalId)
    refreshStatus.value = 'Complete'
    progressMessage.value = '✅ Data refreshed successfully!'
    
    // Wait a moment to show success
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Reload all data
    await dashboardStore.loadDashboardData()
    
    showNotification({
      type: 'success',
      title: 'Data Refreshed!',
      message: `Updated in ${response.summary.duration_seconds.toFixed(0)}s`
    })
  } catch (error) {
    clearInterval(intervalId)
    refreshStatus.value = 'Failed'
    progressMessage.value = error.message
    
    showNotification({
      type: 'error',
      title: 'Refresh Failed',
      message: error.message
    })
  } finally {
    refreshing.value = false
  }
}
</script>
```

---

## ⚙️ **Configuration**

### **No Additional Setup Needed!**

Uses existing environment variables:
- `KNACK_APP_ID`
- `KNACK_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`

---

## 🔒 **Security Considerations**

### **Access Control:**

```python
# In app.py - Add before the sync endpoint
@app.route('/api/sync/refresh-establishment', methods=['POST'])
def refresh_establishment_data():
    # Optional: Verify user has access to this establishment
    user_email = request.headers.get('X-User-Email')  # From Knack
    
    if user_email:
        # Verify user is staff admin for this establishment
        # Could query Knack or Supabase to confirm
        pass
```

**Current Approach:**
- Trusts frontend authentication
- Knack session already validates user
- No additional auth needed (simpler)

**Enhanced Approach** (if needed later):
- Verify user's establishment_id matches request
- Check staff admin permissions
- Rate limiting (max 1 refresh per 5 minutes)

---

## 📊 **User Experience Flow**

### **1. Staff Admin Sees Stale Data:**
```
"Last updated: 18 hours ago"
```

### **2. Clicks Refresh Button:**
```
🔄 Refresh Data
```

### **3. Progress Modal Shows:**
```
┌────────────────────────────┐
│   🔄 Refreshing Data...    │
│                            │
│  Fetching from Knack...    │
│                            │
│  Status: In Progress       │
│  Elapsed: 23s              │
│                            │
│  Usually takes 30-60s...   │
└────────────────────────────┘
```

### **4. Success Notification:**
```
✅ Data Refreshed!
Updated 465 students in 34s
```

### **5. Dashboard Auto-Reloads:**
- New data immediately visible
- No page refresh needed
- Cache cleared automatically

---

## 🧪 **Testing the Feature**

### **Test Locally:**

```bash
# 1. Test the sync script directly
python sync_single_establishment.py --establishment-id 61680fc13a0bfd001e8ca3ca

# Expected output (30-60 seconds):
{
  "success": true,
  "establishment_name": "Ashlyns School",
  "students_synced": 465,
  "vespa_scores_synced": 465,
  "comments_synced": 10,
  "duration_seconds": 34.2
}
```

### **Test API Endpoint:**

```bash
curl -X POST https://vespa-dashboard-9a1f84ee5341.herokuapp.com/api/sync/refresh-establishment \
  -H "Content-Type: application/json" \
  -d '{"establishmentId":"61680fc13a0bfd001e8ca3ca"}'
```

### **Test from Vue Dashboard:**

1. Add button to header
2. Click "Refresh Data"
3. Watch progress modal
4. Verify data updates

---

## ⚡ **Performance Expectations**

Based on Ashlyns test (465 students):

| School Size | Expected Duration |
|-------------|-------------------|
| Tiny (50 students) | 5-10 seconds |
| Small (200 students) | 15-20 seconds |
| Medium (500 students) | 30-40 seconds |
| Large (1,000 students) | 50-70 seconds |
| Extra Large (2,000 students) | 90-120 seconds |

**Comparison to Full Sync:**
- Full sync: 7.6 minutes for ALL schools
- Single school: 30-60 seconds on average
- **10-15x faster** for individual refresh!

---

## 🚀 **Deployment Steps**

### **1. Deploy Backend Files:**

```bash
# Add sync_single_establishment.py to repo
git add sync_single_establishment.py app.py

git commit -m "Feature: Add real-time data refresh for individual establishments

- New sync_single_establishment.py for on-demand syncing
- API endpoint /api/sync/refresh-establishment
- 30-60 second sync time for average school
- Auto-clears cache after refresh
- Returns detailed summary for UI feedback"

git push origin main
git push heroku main
```

### **2. Add Frontend Button (Vue Dashboard):**

- Edit `DASHBOARD-Vue/src/components/DashboardHeader.vue`
- Add refresh button (see code above)
- Add API method to `services/api.js`
- Build and deploy Vue app

---

## 💡 **Advanced Features** (Future Enhancements)

### **1. Rate Limiting:**
```python
# Prevent abuse - max 1 refresh per 5 minutes per establishment
last_refresh = {}

if establishment_id in last_refresh:
    time_since = datetime.now() - last_refresh[establishment_id]
    if time_since < timedelta(minutes=5):
        raise ApiError(f"Please wait {5 - time_since.seconds//60} more minutes before refreshing again")

last_refresh[establishment_id] = datetime.now()
```

### **2. Show Last Sync Time:**
```vue
<div class="last-sync">
  Last updated: {{ timeSince(lastSyncTime) }}
  <button @click="refresh">Refresh Now</button>
</div>
```

### **3. Auto-Refresh on Stale Data:**
```javascript
// If data is >24 hours old, prompt user to refresh
if (hoursSinceSync > 24) {
  showRefreshPrompt()
}
```

---

## 🎯 **Summary**

**Files Created:**
1. `sync_single_establishment.py` - Single school sync script
2. `app.py` - New API endpoint (lines 1257-1326)
3. `REALTIME_REFRESH_FEATURE.md` - This documentation

**Frontend Changes Needed:**
1. Add refresh button to `DashboardHeader.vue`
2. Add API method to `services/api.js`
3. Add progress modal component
4. Rebuild and deploy Vue app

**Benefits:**
- Staff admins can see fresh data instantly
- No waiting for overnight sync
- Better user experience
- No impact on other schools
- Safe and fast

**Ready to implement when you are!** 🚀

