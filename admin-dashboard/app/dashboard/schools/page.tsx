'use client'

import { useState, useEffect } from 'react'
import { supabase, type Establishment } from '@/lib/supabase'
import { School, Users, Search, TrendingUp, BarChart3, X } from 'lucide-react'

type SchoolStats = {
  totalStudents: number
  studentsWithVESPA: number
  completionRate: number
  averageVESPA: number
  cycle1Complete: number
  cycle2Complete: number
  cycle3Complete: number
}

export default function SchoolsPage() {
  const [schools, setSchools] = useState<Establishment[]>([])
  const [filteredSchools, setFilteredSchools] = useState<Establishment[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [schoolStats, setSchoolStats] = useState<Map<string, SchoolStats>>(new Map())
  const [selectedSchool, setSelectedSchool] = useState<Establishment | null>(null)
  const [selectedSchoolStats, setSelectedSchoolStats] = useState<SchoolStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingStats, setLoadingStats] = useState(false)

  useEffect(() => {
    loadSchools()
  }, [])

  useEffect(() => {
    // Filter schools based on search
    if (searchTerm) {
      const filtered = schools.filter(school =>
        school.name.toLowerCase().includes(searchTerm.toLowerCase())
      )
      setFilteredSchools(filtered)
    } else {
      setFilteredSchools(schools)
    }
  }, [searchTerm, schools])

  async function loadSchools() {
    setLoading(true)
    try {
      const { data: establishments, error } = await supabase
        .from('establishments')
        .select('*')
        .order('name')

      if (error) throw error

      if (establishments) {
        setSchools(establishments)
        setFilteredSchools(establishments)
        
        // Don't load stats on page load - only when clicking a school
        // This makes page load MUCH faster
      }
    } catch (error) {
      console.error('Error loading schools:', error)
    }
    setLoading(false)
  }

  async function loadBasicSchoolStats(schoolId: string) {
    try {
      const { count } = await supabase
        .from('students')
        .select('*', { count: 'exact', head: true })
        .eq('establishment_id', schoolId)
        .eq('academic_year', '2025/2026')

      setSchoolStats(prev => new Map(prev).set(schoolId, {
        totalStudents: count || 0,
        studentsWithVESPA: 0,
        completionRate: 0,
        averageVESPA: 0,
        cycle1Complete: 0,
        cycle2Complete: 0,
        cycle3Complete: 0
      }))
    } catch (error) {
      console.error('Error loading stats for school:', error)
    }
  }

  async function viewSchoolDetails(school: Establishment) {
    setSelectedSchool(school)
    setLoadingStats(true)
    
    try {
      // Get all students for this school (current year)
      const { data: students } = await supabase
        .from('students')
        .select('id')
        .eq('establishment_id', school.id)
        .eq('academic_year', '2025/2026')

      if (!students || students.length === 0) {
        setSelectedSchoolStats({
          totalStudents: 0,
          studentsWithVESPA: 0,
          completionRate: 0,
          averageVESPA: 0,
          cycle1Complete: 0,
          cycle2Complete: 0,
          cycle3Complete: 0
        })
        setLoadingStats(false)
        return
      }

      const studentIds = students.map(s => s.id)

      // Get VESPA scores for these students
      const { data: scores } = await supabase
        .from('vespa_scores')
        .select('student_id, cycle, overall')
        .in('student_id', studentIds)
        .eq('academic_year', '2025/2026')

      // Calculate stats
      const uniqueStudentsWithVESPA = new Set(scores?.map(s => s.student_id) || []).size
      const cycle1Students = new Set(scores?.filter(s => s.cycle === 1).map(s => s.student_id) || []).size
      const cycle2Students = new Set(scores?.filter(s => s.cycle === 2).map(s => s.student_id) || []).size
      const cycle3Students = new Set(scores?.filter(s => s.cycle === 3).map(s => s.student_id) || []).size
      
      const overallScores = scores?.filter(s => s.overall !== null).map(s => s.overall) || []
      const averageVESPA = overallScores.length > 0
        ? overallScores.reduce((a, b) => a + (b || 0), 0) / overallScores.length
        : 0

      const completionRate = students.length > 0
        ? (uniqueStudentsWithVESPA / students.length) * 100
        : 0

      setSelectedSchoolStats({
        totalStudents: students.length,
        studentsWithVESPA: uniqueStudentsWithVESPA,
        completionRate: Math.round(completionRate),
        averageVESPA: Math.round(averageVESPA * 10) / 10,
        cycle1Complete: cycle1Students,
        cycle2Complete: cycle2Students,
        cycle3Complete: cycle3Students
      })
    } catch (error) {
      console.error('Error loading school details:', error)
    }
    setLoadingStats(false)
  }

  if (loading) {
    return <div className="text-center py-12">Loading schools...</div>
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Schools Overview</h1>

      {/* Search Bar */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search schools by name..."
            className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-gray-900 bg-white"
          />
          <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
        </div>
        <p className="text-sm text-gray-600 mt-2">
          Showing {filteredSchools.length} of {schools.length} schools
        </p>
      </div>

      {/* Schools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredSchools.map((school) => (
          <button
            key={school.id}
            onClick={() => viewSchoolDetails(school)}
            className="bg-white rounded-lg shadow p-6 hover:shadow-xl transition-all text-left hover:scale-105"
          >
            <div className="flex items-start space-x-3">
              <div className="bg-blue-100 p-3 rounded-lg">
                <School className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 mb-2">{school.name}</h3>
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <Users className="w-4 h-4" />
                  <span>Click for details</span>
                </div>
                {school.is_australian && (
                  <span className="inline-block mt-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">
                    Australian
                  </span>
                )}
                <div className="mt-3 text-blue-600 text-sm font-medium">
                  Click for details →
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* School Detail Modal */}
      {selectedSchool && (
        <SchoolDetailModal
          school={selectedSchool}
          stats={selectedSchoolStats}
          loading={loadingStats}
          onClose={() => setSelectedSchool(null)}
        />
      )}
    </div>
  )
}

function SchoolDetailModal({ school, stats, loading, onClose }: {
  school: Establishment
  stats: SchoolStats | null
  loading: boolean
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">{school.name}</h2>
            <p className="text-sm text-gray-600">Academic Year: 2025/2026</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 p-2 hover:bg-gray-100 rounded-lg"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading ? (
            <div className="text-center py-12 text-gray-500">
              Loading school statistics...
            </div>
          ) : stats ? (
            <>
              {/* Overview Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <StatBox
                  label="Total Students"
                  value={stats.totalStudents}
                  icon={<Users className="w-5 h-5" />}
                  color="bg-blue-100 text-blue-600"
                />
                <StatBox
                  label="With VESPA Data"
                  value={stats.studentsWithVESPA}
                  icon={<BarChart3 className="w-5 h-5" />}
                  color="bg-green-100 text-green-600"
                />
                <StatBox
                  label="Completion Rate"
                  value={`${stats.completionRate}%`}
                  icon={<TrendingUp className="w-5 h-5" />}
                  color="bg-purple-100 text-purple-600"
                />
                <StatBox
                  label="Avg VESPA Score"
                  value={stats.averageVESPA || 'N/A'}
                  icon={<BarChart3 className="w-5 h-5" />}
                  color="bg-orange-100 text-orange-600"
                />
              </div>

              {/* Cycle Completion */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h3 className="font-semibold text-gray-800 mb-4">Cycle Completion</h3>
                <div className="space-y-3">
                  <CycleBar
                    label="Cycle 1"
                    completed={stats.cycle1Complete}
                    total={stats.totalStudents}
                  />
                  <CycleBar
                    label="Cycle 2"
                    completed={stats.cycle2Complete}
                    total={stats.totalStudents}
                  />
                  <CycleBar
                    label="Cycle 3"
                    completed={stats.cycle3Complete}
                    total={stats.totalStudents}
                  />
                </div>
              </div>

              {/* Data Completeness */}
              <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-2">Data Completeness</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-blue-700">Students with data:</span>
                    <span className="font-semibold ml-2">{stats.studentsWithVESPA}/{stats.totalStudents}</span>
                  </div>
                  <div>
                    <span className="text-blue-700">Missing data:</span>
                    <span className="font-semibold ml-2">{stats.totalStudents - stats.studentsWithVESPA}</span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-gray-500">
              No data available for this school
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatBox({ label, value, icon, color }: {
  label: string
  value: string | number
  icon: React.ReactNode
  color: string
}) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <div className={`${color} w-10 h-10 rounded-lg flex items-center justify-center mb-3`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      <div className="text-xs text-gray-600 mt-1">{label}</div>
    </div>
  )
}

function CycleBar({ label, completed, total }: {
  label: string
  completed: number
  total: number
}) {
  const percentage = total > 0 ? (completed / total) * 100 : 0

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-600">{completed}/{total} ({Math.round(percentage)}%)</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
