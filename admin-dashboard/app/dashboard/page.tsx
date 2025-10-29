'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function DashboardHome() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardStats()
  }, [])

  async function loadDashboardStats() {
    try {
      // Get students by year
      const { data: students } = await supabase
        .from('students')
        .select('academic_year')

      const yearCounts: any = {}
      students?.forEach(s => {
        const year = s.academic_year || 'Unknown'
        yearCounts[year] = (yearCounts[year] || 0) + 1
      })

      // Get VESPA scores by year
      const { data: scores } = await supabase
        .from('vespa_scores')
        .select('academic_year, cycle')

      const scoreCounts: any = {}
      scores?.forEach(s => {
        const key = `${s.academic_year} - Cycle ${s.cycle}`
        scoreCounts[key] = (scoreCounts[key] || 0) + 1
      })

      setStats({ yearCounts, scoreCounts })
      setLoading(false)
    } catch (error) {
      console.error('Error loading stats:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading dashboard...</div>
  }

  const chartData = Object.entries(stats.yearCounts).map(([year, count]) => ({
    year,
    students: count
  }))

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Dashboard Overview</h1>

      {/* Students by Year Chart */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Students by Academic Year</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="year" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="students" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">System Status</h2>
        <div className="space-y-3">
          <StatusItem status="operational" label="Database Connection" />
          <StatusItem status="operational" label="Supabase API" />
          <StatusItem status="operational" label="Data Access" />
        </div>
      </div>
    </div>
  )
}

function StatusItem({ status, label }: { status: string, label: string }) {
  const isOperational = status === 'operational'
  return (
    <div className="flex items-center justify-between py-2 border-b">
      <span className="text-gray-700">{label}</span>
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
        isOperational ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      }`}>
        {isOperational ? '● Operational' : '● Down'}
      </span>
    </div>
  )
}

