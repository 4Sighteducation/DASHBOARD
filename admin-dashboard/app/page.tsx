'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function Home() {
  const router = useRouter()
  const [stats, setStats] = useState({
    totalStudents: 0,
    currentYearStudents: 0,
    vespaScores: 0,
    establishments: 0,
    loading: true
  })

  useEffect(() => {
    loadStats()
  }, [])

  async function loadStats() {
    try {
      // Get total students
      const { count: totalStudents } = await supabase
        .from('students')
        .select('*', { count: 'exact', head: true })

      // Get current year students (2025/2026)
      const { count: currentYearStudents } = await supabase
        .from('students')
        .select('*', { count: 'exact', head: true })
        .eq('academic_year', '2025/2026')

      // Get VESPA scores count
      const { count: vespaScores } = await supabase
        .from('vespa_scores')
        .select('*', { count: 'exact', head: true })

      // Get establishments count
      const { count: establishments } = await supabase
        .from('establishments')
        .select('*', { count: 'exact', head: true })

      setStats({
        totalStudents: totalStudents || 0,
        currentYearStudents: currentYearStudents || 0,
        vespaScores: vespaScores || 0,
        establishments: establishments || 0,
        loading: false
      })
    } catch (error) {
      console.error('Error loading stats:', error)
      setStats(prev => ({ ...prev, loading: false }))
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            VESPA Database Admin Dashboard
          </h1>
          <p className="text-gray-600">
            Comprehensive database management and monitoring
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Students"
            value={stats.loading ? '...' : stats.totalStudents.toLocaleString()}
            description="All academic years"
            icon="👥"
            color="bg-blue-500"
          />
          <StatCard
            title="Current Year"
            value={stats.loading ? '...' : stats.currentYearStudents.toLocaleString()}
            description="2025/2026"
            icon="📚"
            color="bg-green-500"
          />
          <StatCard
            title="VESPA Scores"
            value={stats.loading ? '...' : stats.vespaScores.toLocaleString()}
            description="All cycles & years"
            icon="📊"
            color="bg-purple-500"
          />
          <StatCard
            title="Schools"
            value={stats.loading ? '...' : stats.establishments.toLocaleString()}
            description="Active establishments"
            icon="🏫"
            color="bg-orange-500"
          />
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <ActionCard
            title="Student Search"
            description="Search and view student records, VESPA scores, and question responses"
            icon="🔍"
            onClick={() => router.push('/dashboard/students')}
          />
          <ActionCard
            title="Sync Monitor"
            description="View sync status, history, and trigger manual syncs"
            icon="🔄"
            onClick={() => router.push('/dashboard/sync')}
          />
          <ActionCard
            title="Data Quality"
            description="Check for duplicates, missing data, and data integrity issues"
            icon="✓"
            onClick={() => router.push('/dashboard/quality')}
          />
          <ActionCard
            title="School Overview"
            description="View statistics and student lists by school"
            icon="🏫"
            onClick={() => router.push('/dashboard/schools')}
          />
          <ActionCard
            title="Export Center"
            description="Export student data, VESPA scores, and reports"
            icon="📥"
            onClick={() => router.push('/dashboard/export')}
          />
          <ActionCard
            title="Bulk Operations"
            description="Perform bulk data operations and cleanup tasks"
            icon="⚙️"
            onClick={() => router.push('/dashboard/bulk')}
          />
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-600 text-sm">
          <p>VESPA Admin Dashboard v1.0 | Connected to Supabase</p>
          <p className="mt-2">For support, contact: tony@vespa.academy</p>
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, description, icon, color }: {
  title: string
  value: string
  description: string
  icon: string
  color: string
}) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div className={`${color} text-white text-3xl rounded-lg p-3`}>
          {icon}
        </div>
      </div>
      <h3 className="text-2xl font-bold text-gray-800 mb-1">{value}</h3>
      <p className="text-sm font-semibold text-gray-700">{title}</p>
      <p className="text-xs text-gray-500 mt-1">{description}</p>
    </div>
  )
}

function ActionCard({ title, description, icon, onClick }: {
  title: string
  description: string
  icon: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="bg-white rounded-lg shadow-md p-6 hover:shadow-xl hover:scale-105 transition-all text-left"
    >
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="text-xl font-bold text-gray-800 mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
      <div className="mt-4 text-blue-600 text-sm font-semibold">
        Open →
      </div>
    </button>
  )
}

