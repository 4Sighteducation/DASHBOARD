'use client'

import { useState, useEffect } from 'react'
import { supabase, type Establishment } from '@/lib/supabase'
import { School, Users } from 'lucide-react'

export default function SchoolsPage() {
  const [schools, setSchools] = useState<Establishment[]>([])
  const [schoolStats, setSchoolStats] = useState<Map<string, any>>(new Map())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSchools()
  }, [])

  async function loadSchools() {
    setLoading(true)
    try {
      // Load establishments
      const { data: establishments } = await supabase
        .from('establishments')
        .select('*')
        .order('name')

      if (establishments) {
        setSchools(establishments)
        
        // Load stats for each school
        for (const school of establishments) {
          const { count } = await supabase
            .from('students')
            .select('*', { count: 'exact', head: true })
            .eq('establishment_id', school.id)
            .eq('academic_year', '2025/2026')

          setSchoolStats(prev => new Map(prev).set(school.id, { studentCount: count || 0 }))
        }
      }
    } catch (error) {
      console.error('Error loading schools:', error)
    }
    setLoading(false)
  }

  if (loading) {
    return <div className="text-center py-12">Loading schools...</div>
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Schools Overview</h1>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <p className="text-gray-600">
          Total Schools: <strong>{schools.length}</strong>
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {schools.map((school) => (
          <div key={school.id} className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
            <div className="flex items-start space-x-3">
              <div className="bg-blue-100 p-3 rounded-lg">
                <School className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 mb-1">{school.name}</h3>
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <Users className="w-4 h-4" />
                  <span>{schoolStats.get(school.id)?.studentCount || 0} students (2025/2026)</span>
                </div>
                {school.is_australian && (
                  <span className="inline-block mt-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">
                    Australian
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

