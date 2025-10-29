'use client'

export default function BulkOperationsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Bulk Operations</h1>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
        <h3 className="font-semibold text-yellow-900 mb-2">⚠️ Caution Required</h3>
        <p className="text-sm text-yellow-800">
          Bulk operations can affect many records at once. Use with care and always backup before proceeding.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <OperationCard
          title="Fix Academic Years"
          description="Recalculate and update academic years based on completion dates"
          status="planned"
        />
        <OperationCard
          title="Merge Duplicates"
          description="Find and merge duplicate student records"
          status="planned"
        />
        <OperationCard
          title="Delete Test Accounts"
          description="Remove test accounts (@vespa.academy emails)"
          status="planned"
        />
        <OperationCard
          title="Recalculate Statistics"
          description="Regenerate school and national statistics"
          status="planned"
        />
      </div>

      <div className="mt-8 bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Bulk Operation History</h2>
        <p className="text-gray-500 text-center py-8">
          No bulk operations have been performed yet
        </p>
      </div>
    </div>
  )
}

function OperationCard({ title, description, status }: {
  title: string
  description: string
  status: string
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6 border-l-4 border-gray-300">
      <h3 className="font-semibold text-gray-800 mb-2">{title}</h3>
      <p className="text-sm text-gray-600 mb-4">{description}</p>
      <div className="flex items-center justify-between">
        <span className="px-3 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
          {status}
        </span>
        <button
          disabled
          className="px-4 py-2 bg-gray-300 text-gray-500 rounded cursor-not-allowed text-sm"
        >
          Coming Soon
        </button>
      </div>
    </div>
  )
}

