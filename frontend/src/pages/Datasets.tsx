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

export default function Datasets() {
  const qc = useQueryClient()
  const { data = [], isLoading } = useQuery({ queryKey: ['datasets'], queryFn: api.listDatasets })
  const del = useMutation({
    mutationFn: api.deleteDataset,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['datasets'] }),
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

      {data.length === 0 ? (
        <div className="text-center py-20 text-gray-600">
          <p className="text-4xl mb-3">📂</p>
          <p>No datasets yet. <Link to="/datasets/upload" className="text-indigo-400 hover:underline">Upload one</Link> to get started.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {data.map(d => (
            <div key={d._id} className="bg-gray-900 border border-white/10 rounded-xl p-5 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <Link to={`/datasets/${d._id}`} className="font-semibold hover:text-indigo-400 transition-colors">{d.name}</Link>
                <p className="text-xs text-gray-500 mt-0.5">{d.filename} · {d.row_count.toLocaleString()} rows · {d.column_count} cols</p>
              </div>
              <span className={`text-xs font-medium px-2 py-1 rounded-full bg-white/5 ${STATUS_COLOR[d.status] || 'text-gray-400'}`}>{d.status}</span>
              <div className="flex gap-2">
                <Link to={`/datasets/${d._id}/review`} className="text-xs text-gray-400 hover:text-white border border-white/10 px-3 py-1.5 rounded-lg transition-colors">Review</Link>
                <Link to={`/datasets/${d._id}/export`} className="text-xs text-gray-400 hover:text-white border border-white/10 px-3 py-1.5 rounded-lg transition-colors">Export</Link>
                <button onClick={() => { if (confirm('Delete dataset?')) del.mutate(d._id) }}
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
