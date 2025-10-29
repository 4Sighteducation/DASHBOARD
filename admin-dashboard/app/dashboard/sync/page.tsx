'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { RefreshCw, CheckCircle, XCircle, Clock } from 'lucide-react'

type SyncLog = {
  id: string
  sync_type: string
  status: string
  started_at: string
  completed_at: string | null
  metadata: any
  records_processed: number | null
  error_message: string | null
}

export default function SyncMonitorPage() {
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSyncLogs()
  }, [])

  async function loadSyncLogs() {
    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('sync_logs')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(20)

      if (error) throw error
      setSyncLogs(data || [])
    } catch (error) {
      console.error('Error loading sync logs:', error)
    }
    setLoading(false)
  }

  function getStatusIcon(status: string) {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'started':
        return <Clock className="w-5 h-5 text-yellow-500" />
      default:
        return <RefreshCw className="w-5 h-5 text-gray-500" />
    }
  }

  function formatDuration(startedAt: string, completedAt: string | null) {
    if (!completedAt) return 'In progress...'
    
    const start = new Date(startedAt)
    const end = new Date(completedAt)
    const durationMs = end.getTime() - start.getTime()
    const minutes = Math.floor(durationMs / 60000)
    const seconds = Math.floor((durationMs % 60000) / 1000)
    
    return `${minutes}m ${seconds}s`
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Sync Monitor</h1>
        <button
          onClick={loadSyncLogs}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Sync Schedule Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <h3 className="font-semibold text-blue-900 mb-2">Scheduled Sync Times (UTC)</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>12:00 AM</strong> - National Averages Calculation</li>
          <li>• <strong>2:00 AM</strong> - Main Database Sync</li>
        </ul>
      </div>

      {/* Sync Logs Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="px-6 py-12 text-center text-gray-500">
            Loading sync logs...
          </div>
        ) : syncLogs.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            No sync logs found
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Records</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {syncLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(log.status)}
                      <span className="text-sm capitalize">{log.status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{log.sync_type}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {new Date(log.started_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {formatDuration(log.started_at, log.completed_at)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {log.records_processed?.toLocaleString() || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

