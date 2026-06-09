import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export default function Export() {
  const { id } = useParams<{ id: string }>()
  const { data: report } = useQuery({ queryKey: ['report', id], queryFn: () => api.getReport(id!) })

  const formats = [
    { fmt: 'csv', label: 'CSV', desc: 'Comma-separated values', icon: '📄' },
    { fmt: 'json', label: 'JSON', desc: 'JSON array of records', icon: '{ }' },
    { fmt: 'excel', label: 'Excel', desc: 'XLSX spreadsheet', icon: '📊' },
  ]

  return (
    <div className="p-8 max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <Link to={`/datasets/${id}`} className="text-gray-500 hover:text-white transition-colors">←</Link>
        <h1 className="text-2xl font-bold">Export Dataset</h1>
      </div>

      <div className="grid gap-4 mb-8">
        {formats.map(({ fmt, label, desc, icon }) => (
          <a key={fmt} href={api.exportUrl(id!, fmt)}
            className="flex items-center gap-4 bg-gray-900 border border-white/10 rounded-xl p-5 hover:border-indigo-500 transition-colors group">
            <span className="text-3xl">{icon}</span>
            <div className="flex-1">
              <p className="font-semibold">{label}</p>
              <p className="text-sm text-gray-500">{desc}</p>
            </div>
            <span className="text-sm text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity">Download →</span>
          </a>
        ))}
      </div>

      {report && (
        <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
          <h2 className="font-semibold mb-4 text-sm uppercase tracking-wide text-gray-400">Processing Report</h2>
          <div className="grid grid-cols-2 gap-3 mb-4">
            {Object.entries(report.label_distribution as Record<string, number>).map(([label, count]) => (
              <div key={label} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2">
                <span className="text-sm">{label}</span>
                <span className="text-sm font-bold text-indigo-400">{count}</span>
              </div>
            ))}
          </div>
          <details className="text-xs">
            <summary className="cursor-pointer text-gray-500 hover:text-white transition-colors">Processing history ({(report.processing_history as unknown[]).length} entries)</summary>
            <pre className="mt-2 bg-black/30 p-3 rounded-lg overflow-x-auto text-gray-400">
              {JSON.stringify(report.processing_history, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  )
}
