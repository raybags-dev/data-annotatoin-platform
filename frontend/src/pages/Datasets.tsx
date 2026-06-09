import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

const STATUS_COLOR: Record<string, string> = {
  uploaded: 'text-gray-400',
  ingested: 'text-blue-400',
  validated: 'text-cyan-400',
  cleaned: 'text-teal-400',
  labeled: 'text-indigo-400',
  exported: 'text-green-400',
}

function fmtSize(bytes: number | null | undefined): string {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

export default function Datasets() {
  const qc = useQueryClient()
  const { data = [], isLoading } = useQuery({ queryKey: ['datasets'], queryFn: api.listDatasets })
  const { data: summary } = useQuery({ queryKey: ['storage-summary'], queryFn: api.storageSummary })
  const del = useMutation({
    mutationFn: api.deleteDataset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['datasets'] })
      qc.invalidateQueries({ queryKey: ['storage-summary'] })
    },
  })

  if (isLoading) return <div className="p-8 text-gray-500 animate-pulse">Loading…</div>

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Datasets</h1>
        <Link to="/datasets/upload" className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded-lg transition-colors">
          + Upload
        </Link>
      </div>

      {/* Storage summary bar */}
      {summary && (
        <div className="mb-6 bg-gray-900/60 border border-white/10 rounded-xl px-5 py-3 flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Total storage used:</span>
            <span className="font-semibold text-indigo-400">{fmtSize(summary.total_bytes)}</span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Datasets:</span>
            <span className="font-semibold">{summary.dataset_count}</span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex-1">
            {/* Simple usage bar — cap at 1 GB for visual scale */}
            <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all"
                style={{ width: `${Math.min(100, (summary.total_bytes / (1024 * 1024 * 1024)) * 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-600 mt-0.5">of 1 GB visual scale</p>
          </div>
        </div>
      )}

      {data.length === 0 ? (
        <div className="text-center py-20 text-gray-600">
          <p className="text-4xl mb-3">📂</p>
          <p>No datasets yet. <Link to="/datasets/upload" className="text-indigo-400 hover:underline">Upload one</Link> to get started.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {data.map(d => (
            <div key={d.id} className="bg-gray-900 border border-white/10 rounded-xl p-5 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <Link to={`/datasets/${d.id}`} className="font-semibold hover:text-indigo-400 transition-colors">{d.name}</Link>
                <p className="text-xs text-gray-500 mt-0.5">
                  {d.filename} · {d.row_count.toLocaleString()} rows · {d.column_count} cols
                  {d.file_size_bytes ? <span className="ml-1 text-gray-600">· {fmtSize(d.file_size_bytes)}</span> : null}
                  {d.kaggle_handle ? <span className="ml-1 text-indigo-600 font-mono"> · {d.kaggle_handle}</span> : null}
                </p>
              </div>
              <span className={`text-xs font-medium px-2 py-1 rounded-full bg-white/5 ${STATUS_COLOR[d.status] || 'text-gray-400'}`}>{d.status}</span>
              <div className="flex gap-2">
                <Link to={`/datasets/${d.id}/review`} className="text-xs text-gray-400 hover:text-white border border-white/10 px-3 py-1.5 rounded-lg transition-colors">Review</Link>
                <Link to={`/datasets/${d.id}/export`} className="text-xs text-gray-400 hover:text-white border border-white/10 px-3 py-1.5 rounded-lg transition-colors">Export</Link>
                <button onClick={() => { if (confirm('Delete dataset?')) del.mutate(d.id) }}
                  className="text-xs text-red-400 hover:text-red-300 border border-white/10 px-3 py-1.5 rounded-lg transition-colors">
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
