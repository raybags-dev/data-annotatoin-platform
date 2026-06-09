import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { DataRecord } from '../lib/types'

export default function Review() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [page, setPage] = useState(0)
  const [override, setOverride] = useState<Record<string, string>>({})
  const LIMIT = 20

  const { data: records = [], isLoading } = useQuery({
    queryKey: ['records', id, page],
    queryFn: () => api.listRecords(id!, page * LIMIT, LIMIT),
  })
  const { data: stats } = useQuery({ queryKey: ['ann-stats', id], queryFn: () => api.annotationStats(id!) })

  const review = useMutation({
    mutationFn: ({ rid, action, label }: { rid: string; action: string; label?: string }) =>
      api.reviewRecord(rid, action, label),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['records', id] }); qc.invalidateQueries({ queryKey: ['ann-stats', id] }) },
  })

  const approveAll = useMutation({
    mutationFn: () => api.approveAll(id!),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['records', id] }); qc.invalidateQueries({ queryKey: ['ann-stats', id] }) },
  })

  if (isLoading) return <div className="p-8 text-gray-500 animate-pulse">Loading records…</div>

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Review Annotations</h1>
        <div className="flex items-center gap-3">
          {stats && (
            <span className="text-xs text-gray-500">
              {stats.by_status?.approved ?? 0} approved · {stats.by_status?.pending ?? 0} pending · {stats.by_status?.rejected ?? 0} rejected
            </span>
          )}
          <button onClick={() => approveAll.mutate()} className="text-sm bg-green-600/20 border border-green-500/40 text-green-400 px-4 py-1.5 rounded-lg hover:bg-green-600/30 transition-colors">
            ✓ Approve All Pending
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {records.map((rec: DataRecord) => {
          const ann = rec.annotation
          const status = ann?.status ?? 'unannotated'
          return (
            <div key={rec.id} className={`bg-gray-900 border rounded-xl p-4 ${status === 'approved' ? 'border-green-500/30' : status === 'rejected' ? 'border-red-500/30' : 'border-white/10'}`}>
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${status === 'approved' ? 'bg-green-500/20 text-green-400' : status === 'rejected' ? 'bg-red-500/20 text-red-400' : 'bg-white/10 text-gray-400'}`}>
                      {status}
                    </span>
                    {ann && <span className="text-xs text-indigo-400 font-medium">{ann.human_label || ann.label}</span>}
                    {ann && <span className="text-xs text-gray-500">{(ann.confidence * 100).toFixed(0)}% confidence</span>}
                  </div>
                  <pre className="text-xs text-gray-400 bg-black/30 rounded-lg p-2 overflow-x-auto max-h-24">
                    {JSON.stringify(rec.cleaned_data || rec.raw_data, null, 2).slice(0, 400)}
                  </pre>
                  {ann?.reasoning && <p className="text-xs text-gray-500 mt-1 italic">"{ann.reasoning}"</p>}
                </div>
                <div className="flex flex-col gap-1.5 shrink-0">
                  <button onClick={() => review.mutate({ rid: rec.id, action: 'approve' })}
                    className="text-xs bg-green-500/10 border border-green-500/30 text-green-400 px-3 py-1 rounded-lg hover:bg-green-500/20 transition-colors">✓</button>
                  <button onClick={() => review.mutate({ rid: rec.id, action: 'reject' })}
                    className="text-xs bg-red-500/10 border border-red-500/30 text-red-400 px-3 py-1 rounded-lg hover:bg-red-500/20 transition-colors">✗</button>
                  <div className="flex gap-1">
                    <input value={override[rec.id] || ''} onChange={e => setOverride(p => ({ ...p, [rec.id]: e.target.value }))}
                      placeholder="Override…" className="w-20 text-xs bg-gray-800 border border-white/10 rounded px-2 py-1 outline-none" />
                    <button onClick={() => review.mutate({ rid: rec.id, action: 'override', label: override[rec.id] })}
                      disabled={!override[rec.id]}
                      className="text-xs text-indigo-400 border border-indigo-500/30 px-2 py-1 rounded disabled:opacity-50 hover:bg-indigo-500/10 transition-colors">→</button>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex justify-center gap-3 mt-6">
        <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
          className="text-sm border border-white/10 px-4 py-1.5 rounded-lg disabled:opacity-40 hover:border-white/30 transition-colors">← Prev</button>
        <span className="text-sm text-gray-500 py-1.5">Page {page + 1}</span>
        <button onClick={() => setPage(p => p + 1)} disabled={records.length < LIMIT}
          className="text-sm border border-white/10 px-4 py-1.5 rounded-lg disabled:opacity-40 hover:border-white/30 transition-colors">Next →</button>
      </div>
    </div>
  )
}
