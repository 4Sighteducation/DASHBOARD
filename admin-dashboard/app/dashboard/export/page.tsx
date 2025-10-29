'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'
import { Download, FileText } from 'lucide-react'

export default function ExportPage() {
  const [exporting, setExporting] = useState(false)
  const [selectedYear, setSelectedYear] = useState('2025/2026')
  const [exportType, setExportType] = useState('students')

  const academicYears = ['2025/2026', '2024/2025', '2023/2024', 'All Years']
  const exportTypes = [
    { value: 'students', label: 'Students Only' },
    { value: 'vespa', label: 'Students + VESPA Scores' },
    { value: 'complete', label: 'Complete Data (Students + VESPA + Questions)' },
  ]

  async function handleExport() {
    setExporting(true)
    try {
      let query = supabase.from('students').select('*')
      
      if (selectedYear !== 'All Years') {
        query = query.eq('academic_year', selectedYear)
      }

      const { data: students, error } = await query

      if (error) throw error

      // Convert to CSV
      if (students && students.length > 0) {
        const csv = convertToCSV(students)
        downloadCSV(csv, `students_${selectedYear}_${new Date().toISOString().split('T')[0]}.csv`)
      } else {
        alert('No data to export')
      }

    } catch (error) {
      console.error('Error exporting:', error)
      alert('Export failed. Check console for details.')
    }
    setExporting(false)
  }

  function convertToCSV(data: any[]) {
    if (data.length === 0) return ''
    
    const headers = Object.keys(data[0])
    const csvRows = []
    
    // Add header row
    csvRows.push(headers.join(','))
    
    // Add data rows
    for (const row of data) {
      const values = headers.map(header => {
        const value = row[header]
        // Escape quotes and wrap in quotes if contains comma
        if (value === null || value === undefined) return ''
        const stringValue = String(value)
        if (stringValue.includes(',') || stringValue.includes('"')) {
          return `"${stringValue.replace(/"/g, '""')}"`
        }
        return stringValue
      })
      csvRows.push(values.join(','))
    }
    
    return csvRows.join('\n')
  }

  function downloadCSV(csv: string, filename: string) {
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.setAttribute('hidden', '')
    a.setAttribute('href', url)
    a.setAttribute('download', filename)
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Export Center</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Export Configuration</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Export Type
            </label>
            <select
              value={exportType}
              onChange={(e) => setExportType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {exportTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
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

          <button
            onClick={handleExport}
            disabled={exporting}
            className="w-full mt-4 flex items-center justify-center space-x-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors"
          >
            {exporting ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>Exporting...</span>
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                <span>Export to CSV</span>
              </>
            )}
          </button>
        </div>

        {/* Export Templates */}
        <div className="mt-8 pt-6 border-t">
          <h3 className="text-lg font-semibold mb-4">Quick Export Templates</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ExportTemplate
              title="Current Year Students"
              description="All students in 2025/2026"
              icon={<FileText className="w-5 h-5" />}
            />
            <ExportTemplate
              title="Archive (2024/2025)"
              description="Historical data from last year"
              icon={<FileText className="w-5 h-5" />}
            />
            <ExportTemplate
              title="All VESPA Scores"
              description="Complete VESPA score database"
              icon={<FileText className="w-5 h-5" />}
            />
            <ExportTemplate
              title="Question Responses"
              description="Individual question-level data"
              icon={<FileText className="w-5 h-5" />}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function ExportTemplate({ title, description, icon }: {
  title: string
  description: string
  icon: React.ReactNode
}) {
  return (
    <div className="border rounded-lg p-4 hover:border-blue-500 hover:shadow-md transition-all cursor-pointer">
      <div className="flex items-start space-x-3">
        <div className="text-blue-600 mt-1">{icon}</div>
        <div>
          <h4 className="font-semibold text-gray-800">{title}</h4>
          <p className="text-sm text-gray-600 mt-1">{description}</p>
        </div>
      </div>
    </div>
  )
}

