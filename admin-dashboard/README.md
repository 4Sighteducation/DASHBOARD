# VESPA Admin Dashboard

Modern admin interface for managing and monitoring the VESPA Database.

## Features

- ✅ **Student Search** - Find and view student records
- ✅ **VESPA Score Viewer** - View all cycles and academic years
- ✅ **Question Responses** - Individual question-level data
- ✅ **Sync Monitor** - Track daily sync status and history
- ✅ **Data Quality** - Check for duplicates and missing data
- ✅ **School Overview** - Statistics per establishment
- ✅ **Export Tools** - Download data as CSV
- ✅ **Bulk Operations** - Data cleanup and maintenance

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS
- **Database:** Supabase (PostgreSQL)
- **Charts:** Recharts
- **Icons:** Lucide React
- **Deployment:** Vercel

## Environment Variables

Create `.env.local` file:

```bash
# Supabase (VESPA Database)
SUPABASE_URL=https://qcdcdzfanrlvdcagmwmg.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Knack (for API access if needed)
KNACK_APP_ID=your_knack_app_id
KNACK_API_KEY=your_knack_api_key
```

## Local Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000
```

## Vercel Deployment

### Setup:

1. **Create new Vercel project**
2. **Import Git repository:** `4Sighteducation/DASHBOARD`
3. **Root Directory:** `DASHBOARD/admin-dashboard` ← IMPORTANT!
4. **Framework:** Next.js (auto-detected)
5. **Environment Variables:** Add all from .env.local
6. **Deploy!**

### Custom Domain:

1. **In Vercel:** Settings → Domains → Add `admin.vespa.academy`
2. **In DNS Provider:** Add CNAME record:
   - Name: `admin`
   - Value: `cname.vercel-dns.com`
3. **Wait for propagation** (5-60 minutes)
4. **Access:** https://admin.vespa.academy

## Features Guide

### Student Search
- Search by email or name
- Filter by academic year
- View complete student profile
- See all VESPA scores
- Export individual student data

### Sync Monitor
- View last 20 sync runs
- See duration and status
- Check for errors
- Track records processed

### Export Center
- Export by academic year
- Export by school
- Multiple format options
- Scheduled exports (future)

## Database Schema

Connects to Supabase tables:
- `students` - Student records
- `vespa_scores` - VESPA assessment scores
- `question_responses` - Individual question responses
- `establishments` - Schools/colleges
- `sync_logs` - Sync history
- `school_statistics` - Calculated statistics
- `national_statistics` - National benchmarks

## Support

For issues or questions:
- Email: tony@vespa.academy
- GitHub: 4Sighteducation/DASHBOARD

## Version

**v1.0.0** - Initial Release (October 2025)

Built with ❤️ for VESPA Academy

