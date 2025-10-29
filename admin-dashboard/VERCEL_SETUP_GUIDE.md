# Vercel Setup Guide - VESPA Admin Dashboard

## 📋 **Step-by-Step Instructions**

### **Step 1: Create New Vercel Project**

1. Go to: https://vercel.com/dashboard
2. Click **"Add New..."** → **"Project"**
3. Click **"Import Git Repository"**

---

### **Step 2: Select Repository**

1. Find repository: **4Sighteducation/DASHBOARD**
2. Click **"Import"**

---

### **Step 3: Configure Project** ⚠️ **CRITICAL!**

**Project Name:**
```
vespa-admin-dashboard
```

**Framework Preset:**
```
Next.js ✓ (should auto-detect)
```

**Root Directory:** ← **MOST IMPORTANT SETTING!**
```
Click "Edit" button
Type exactly: DASHBOARD/admin-dashboard

OR if that doesn't work, try: admin-dashboard
```

**Build Command:**
```
npm run build
(leave as default)
```

**Output Directory:**
```
.next
(leave as default)
```

---

### **Step 4: Environment Variables**

Click **"Environment Variables"** dropdown

**Add each variable:**

| Variable Name | Value | Environment |
|--------------|-------|-------------|
| `SUPABASE_URL` | `https://qcdcdzfanrlvdcagmwmg.supabase.co` | ☑️ All |
| `SUPABASE_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` | ☑️ All |
| `KNACK_APP_ID` | `5ee90912c38ae...` | ☑️ All |
| `KNACK_API_KEY` | `8f733aa5-dd35-4464-83...` | ☑️ All |

**For each variable:**
1. Type the name
2. Paste the value
3. Make sure **all 3 checkboxes** are checked:
   - ☑️ Production
   - ☑️ Preview
   - ☑️ Development
4. Click **"Add"**

---

### **Step 5: Deploy**

1. Click **"Deploy"** button
2. Wait 2-5 minutes
3. Should show: **"Deployment completed"** ✅

**If it fails:**
- Check build logs
- Verify Root Directory is correct
- Ensure environment variables are set

---

### **Step 6: Add Custom Domain** (admin.vespa.academy)

#### **6a. In Vercel:**

1. Go to your project: **vespa-admin-dashboard**
2. Click **"Settings"** → **"Domains"**
3. Click **"Add"** button
4. Type: `admin.vespa.academy`
5. Click **"Add"**

**Vercel will show:**
```
⚠️ Invalid Configuration

Add this DNS record:
Type: CNAME
Name: admin
Value: cname.vercel-dns.com
```

---

#### **6b. In Your DNS Provider:**

**Go to wherever vespa.academy DNS is hosted** (Cloudflare? Namecheap? GoDaddy?)

**Add NEW CNAME record:**

**Cloudflare:**
```
Type: CNAME
Name: admin
Target: cname.vercel-dns.com
Proxy: DNS only (gray cloud)
```

**Namecheap/GoDaddy:**
```
Record Type: CNAME
Host: admin
Value: cname.vercel-dns.com
TTL: Automatic
```

**Save the DNS record**

---

#### **6c. Wait for DNS Propagation**

**Time:** 5 minutes to 1 hour (usually 10-15 minutes)

**Check in Vercel:**
- Domains page will update to show: **"Valid Configuration" ✅**

**Test:**
- Visit https://admin.vespa.academy
- Should load your admin dashboard!

---

## 🎯 **Final Configuration**

**After setup, you'll have:**

```
Main Website (Existing):
  Domain: www.vespa.academy
  Vercel Project: vespa-academy-website
  
Admin Dashboard (New):
  Domain: admin.vespa.academy
  Vercel Project: vespa-admin-dashboard
  Root: DASHBOARD/admin-dashboard
```

**Both from same Git organization, separate deployments!**

---

## ✅ **Verification Steps**

**1. Check Deployment:**
- Visit the Vercel-provided URL (e.g., vespa-admin-dashboard.vercel.app)
- Should see admin dashboard homepage

**2. Check Database Connection:**
- Homepage should show statistics (student counts, etc.)
- If shows "0" for everything → check environment variables

**3. Check Custom Domain:**
- Visit admin.vespa.academy
- Should redirect to HTTPS automatically
- Should load admin dashboard

---

## 🆘 **Troubleshooting**

### **Build Fails:**
```
Error: Cannot find module 'next'
```
**Fix:** Root Directory might be wrong. Try `admin-dashboard` instead of `DASHBOARD/admin-dashboard`

### **Shows 0 for Everything:**
```
Stats show: 0 students, 0 scores
```
**Fix:** Environment variables not set. Check Settings → Environment Variables

### **Domain Not Working:**
```
admin.vespa.academy → Site not found
```
**Fix:** DNS not propagated yet. Wait 15 more minutes or check DNS records are correct.

---

## 📧 **Support**

If you have issues:
1. Check Vercel deployment logs
2. Check browser console for errors
3. Contact: tony@vespa.academy

---

**Good luck! 🚀**

