'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'
import { AlertCircle, CheckCircle, Search } from 'lucide-react'

export default function DataQualityPage() {
  const [checking, setChecking] = useState(false)
  const [results, setResults] = useState<any>(null)

  async function runQualityCheck() {
    setChecking(true)
    const checks: any = {
      duplicateStudents: [],
      orphanedVESPA: 0,
      orphanedQuestions: 0,
      missingAcademicYear: 0,
      totalChecks: 0
    }

    try {
      // Check for duplicate students (same email in same year)
      const { data: students } = await supabase
        .from('students')
        .select('email, academic_year')

      const emailYearMap = new Map()
      students?.forEach(s => {
        const key = `${s.email}_${s.academic_year}`
        emailYearMap.set(key, (emailYearMap.get(key) || 0) + 1)
      })

      checks.duplicateStudents = Array.from(emailYearMap.entries())
        .filter(([_, count]) => count > 1)
        .map(([key, count]) => ({ key, count }))

      // Check for VESPA scores without students
      const { count: orphanedVESPA } = await supabase
        .from('vespa_scores')
        .select('*', { count: 'exact', head: true })
        .is('student_id', null)

      checks.orphanedVESPA = orphanedVESPA || 0

      // Check for question responses without students
      const { count: orphanedQuestions } = await supabase
        .from('question_responses')
        .select('*', { count: 'exact', head: true })
        .is('student_id', null)

      checks.orphanedQuestions = orphanedQuestions || 0

      // Check for missing academic year
      const { count: missingYear } = await supabase
        .from('students')
        .select('*', { count: 'exact', head: true })
        .is('academic_year', null)

      checks.missingAcademicYear = missingYear || 0

      checks.totalChecks = 4
      setResults(checks)
    } catch (error) {
      console.error('Error running quality check:', error)
      alert('Quality check failed. Check console for details.')
    }
    setChecking(false)
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Data Quality Check</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <p className="text-gray-600 mb-4">
          Run comprehensive data quality checks to identify issues
        </p>
        <button
          onClick={runQualityCheck}
          disabled={checking}
          className="flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
        >
          <Search className="w-5 h-5" />
          <span>{checking ? 'Checking...' : 'Run Quality Check'}</span>
        </button>
      </div>

      {results && (
        <div className="space-y-4">
          <ResultCard
            title="Duplicate Students"
            count={results.duplicateStudents.length}
            status={results.duplicateStudents.length === 0 ? 'good' : 'warning'}
            description={results.duplicateStudents.length === 0 
              ? 'No duplicates found' 
              : `${results.duplicateStudents.length} duplicate email+year combinations`}
          />
          <ResultCard
            title="Orphaned VESPA Scores"
            count={results.orphanedVESPA}
            status={results.orphanedVESPA === 0 ? 'good' : 'error'}
            description={results.orphanedVESPA === 0
              ? 'All VESPA scores linked to students'
              : `${results.orphanedVESPA} scores without student link`}
          />
          <ResultCard
            title="Orphaned Question Responses"
            count={results.orphanedQuestions}
            status={results.orphanedQuestions === 0 ? 'good' : 'error'}
            description={results.orphanedQuestions === 0
              ? 'All responses linked to students'
              : `${results.orphanedQuestions} responses without student link`}
          />
          <ResultCard
            title="Missing Academic Year"
            count={results.missingAcademicYear}
            status={results.missingAcademicYear === 0 ? 'good' : 'warning'}
            description={results.missingAcademicYear === 0
              ? 'All students have academic year assigned'
              : `${results.missingAcademicYear} students missing academic year`}
          />
        </div>
      )}
    </div>
  )
}

function ResultCard({ title, count, status, description }: {
  title: string
  count: number
  status: 'good' | 'warning' | 'error'
  description: string
}) {
  const statusColors = {
    good: 'bg-green-50 border-green-200',
    warning: 'bg-yellow-50 border-yellow-200',
    error: 'bg-red-50 border-red-200'
  }

  const iconColors = {
    good: 'text-green-600',
    warning: 'text-yellow-600',
    error: 'text-red-600'
  }

  return (
    <div className={`border rounded-lg p-6 ${statusColors[status]}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            {status === 'good' ? (
              <CheckCircle className={`w-6 h-6 ${iconColors[status]}`} />
            ) : (
              <AlertCircle className={`w-6 h-6 ${iconColors[status]}`} />
            )}
            <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
          </div>
          <p className="text-sm text-gray-600">{description}</p>
        </div>
        <div className="text-3xl font-bold text-gray-800">{count}</div>
      </div>
    </div>
  )
}

