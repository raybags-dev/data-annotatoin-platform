import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import PipelineProgress from '../components/PipelineProgress'

const STAGES = ['ingest', 'validate', 'clean', 'label']

export default function DatasetDetail() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [categories, setCategories] = useState('')
  const [running, setRunning] = useState<string | null>(null)

  const { data: ds, isLoading } = useQuery({ queryKey: ['dataset', id], queryFn: () => api.getDataset(id!), refetchInterval: running ? 2000 : false })

  const runStage = useMutation({
    mutationFn: (stage: string) => { setRunning(stage); return api.runStage(id!, stage) },
    onSettled: () => { setRunning(null); qc.invalidateQueries({ queryKey: ['dataset', id] }) },
  })

  const runAll = useMutation({
    mutationFn: () => { setRunning('all'); return api.runPipeline(id!) },
    onSettled: () => { setRunning(null); qc.invalidateQueries({ queryKey: ['dataset', id] }) },
  })

  const saveConfig = useMutation({
    mutationFn: () => api.setLabelingConfig(id!, { categories: categories.split(',').map(s => s.trim()).filter(Boolean), model: 'llama3.2:3b' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dataset', id] }),
  })

  if (isLoading || !ds) return <div className="p-8 text-gray-500 animate-pulse">Loading…</div>

  return (
    <div className="p-8 max-w-3xl space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{ds.name}</h1>
          <p className="text-sm text-gray-500 mt-1">{ds.filename} · {ds.row_count.toLocaleString()} rows · {ds.column_count} cols · <span className="text-indigo-400">{ds.status}</span></p>
        </div>
        <div className="flex gap-2">
          <Link to={`/datasets/${id}/review`} className="text-sm border border-white/10 px-3 py-1.5 rounded-lg hover:border-indigo-500 transition-colors">Review</Link>
          <Link to={`/datasets/${id}/export`} className="text-sm border border-white/10 px-3 py-1.5 rounded-lg hover:border-indigo-500 transition-colors">Export</Link>
        </div>
      </div>

      <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
        <h2 className="font-semibold mb-4 text-sm uppercase tracking-wide text-gray-400">Pipeline</h2>
        <PipelineProgress history={ds.processing_history} status={ds.status} />
        <div className="flex flex-wrap gap-2 mt-5">
          <button onClick={() => runAll.mutate()} disabled={!!running}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition-colors">
            {running === 'all' ? '⏳ Running…' : '▶ Run Full Pipeline'}
          </button>
          {STAGES.map(s => (
            <button key={s} onClick={() => runStage.mutate(s)} disabled={!!running}
              className="text-sm border border-white/10 px-3 py-1.5 rounded-lg hover:border-indigo-500 disabled:opacity-50 transition-colors capitalize">
              {running === s ? '⏳' : '▸'} {s}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
        <h2 className="font-semibold mb-3 text-sm uppercase tracking-wide text-gray-400">Label Config</h2>
        <p className="text-xs text-gray-500 mb-2">Comma-separated categories (e.g. spam,ham or positive,negative,neutral)</p>
        <div className="flex gap-2">
          <input value={categories || ds.labeling_config.categories.join(', ')} onChange={e => setCategories(e.target.value)}
            placeholder="category1, category2, …"
            className="flex-1 bg-gray-800 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-indigo-500" />
          <button onClick={() => saveConfig.mutate()} className="text-sm bg-indigo-600/20 border border-indigo-500/40 text-indigo-400 px-4 py-2 rounded-lg hover:bg-indigo-600/30 transition-colors">
            Save
          </button>
        </div>
      </div>

      {ds.validation_report && (
        <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
          <h2 className="font-semibold mb-3 text-sm uppercase tracking-wide text-gray-400">Validation Report</h2>
          <div className="grid grid-cols-3 gap-3 mb-3">
            {[['Rows', ds.validation_report.total_rows], ['Duplicates', ds.validation_report.duplicate_rows], ['Issues', ds.validation_report.issues.length]].map(([k, v]) => (
              <div key={k} className="bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">{k}</p>
                <p className="text-xl font-bold mt-0.5">{v}</p>
              </div>
            ))}
          </div>
          {ds.validation_report.issues.map((iss, i) => (
            <p key={i} className="text-xs text-yellow-400 bg-yellow-400/10 px-3 py-1.5 rounded mt-1">⚠ {iss}</p>
          ))}
        </div>
      )}

      {ds.cleaning_report && (
        <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
          <h2 className="font-semibold mb-3 text-sm uppercase tracking-wide text-gray-400">Cleaning Report</h2>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(ds.cleaning_report).map(([k, v]) => (
              <div key={k} className="bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">{k.replace(/_/g, ' ')}</p>
                <p className="text-xl font-bold mt-0.5">{v as number}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
