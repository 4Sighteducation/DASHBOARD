'use client'

import { useState, useEffect } from 'react'
import { supabase, type Student, type VESPAScore } from '@/lib/supabase'
import { Search, Download, Eye } from 'lucide-react'

export default function StudentsPage() {
  const [students, setStudents] = useState<Student[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedYear, setSelectedYear] = useState('2025/2026')
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null)
  const [vespaScores, setVespaScores] = useState<VESPAScore[]>([])

  const academicYears = ['2025/2026', '2024/2025', '2023/2024', '2022/2023', 'All Years']

  async function searchStudents() {
    setLoading(true)
    try {
      let query = supabase
        .from('students')
        .select('*')
        .order('name')
        .limit(100)

      if (selectedYear !== 'All Years') {
        query = query.eq('academic_year', selectedYear)
      }

      if (searchTerm) {
        query = query.or(`email.ilike.%${searchTerm}%,name.ilike.%${searchTerm}%`)
      }

      const { data, error } = await query

      if (error) throw error
      setStudents(data || [])
    } catch (error) {
      console.error('Error searching students:', error)
    }
    setLoading(false)
  }

  async function viewStudentDetails(student: Student) {
    setSelectedStudent(student)
    
    // Fetch VESPA scores
    const { data } = await supabase
      .from('vespa_scores')
      .select('*')
      .eq('student_id', student.id)
      .order('cycle')

    setVespaScores(data || [])
  }

  useEffect(() => {
    searchStudents()
  }, [selectedYear])

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Student Search</h1>

      {/* Search Bar */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search by Email or Name
            </label>
            <div className="relative">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && searchStudents()}
                placeholder="Type email or name..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <Search className="absolute right-3 top-2.5 w-5 h-5 text-gray-400" />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Academic Year
            </label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {academicYears.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={searchStudents}
          disabled={loading}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* Results */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-800">
            Results: {students.length} students found
          </h2>
        </div>

        {students.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            No students found. Try adjusting your search or filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Year</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Year Group</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {students.map((student) => (
                  <tr key={student.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-900">{student.email}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">{student.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{student.academic_year}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{student.year_group}</td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        onClick={() => viewStudentDetails(student)}
                        className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Student Detail Modal */}
      {selectedStudent && (
        <StudentDetailModal
          student={selectedStudent}
          vespaScores={vespaScores}
          onClose={() => setSelectedStudent(null)}
        />
      )}
    </div>
  )
}

function StudentDetailModal({ student, vespaScores, onClose }: {
  student: Student
  vespaScores: VESPAScore[]
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-800">Student Details</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        <div className="p-6">
          {/* Student Info */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">Student Information</h3>
            <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg">
              <InfoRow label="Email" value={student.email} />
              <InfoRow label="Name" value={student.name} />
              <InfoRow label="Academic Year" value={student.academic_year} />
              <InfoRow label="Year Group" value={student.year_group} />
              <InfoRow label="Knack ID" value={student.knack_id} />
            </div>
          </div>

          {/* VESPA Scores */}
          <div>
            <h3 className="text-lg font-semibold mb-3">VESPA Scores</h3>
            {vespaScores.length === 0 ? (
              <p className="text-gray-500">No VESPA scores found</p>
            ) : (
              <div className="space-y-4">
                {vespaScores.map((score) => (
                  <div key={score.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-center mb-3">
                      <h4 className="font-semibold">Cycle {score.cycle}</h4>
                      <span className="text-sm text-gray-600">
                        {score.completion_date || 'No date'}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
                      <ScoreBox label="Vision" value={score.vision} />
                      <ScoreBox label="Effort" value={score.effort} />
                      <ScoreBox label="Systems" value={score.systems} />
                      <ScoreBox label="Practice" value={score.practice} />
                      <ScoreBox label="Attitude" value={score.attitude} />
                      <ScoreBox label="Overall" value={score.overall} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string, value: string }) {
  return (
    <div>
      <dt className="text-sm font-medium text-gray-500">{label}</dt>
      <dd className="mt-1 text-sm text-gray-900">{value || 'N/A'}</dd>
    </div>
  )
}

function ScoreBox({ label, value }: { label: string, value: number | null }) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold text-blue-600">
        {value !== null ? value : '-'}
      </div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  )
}

