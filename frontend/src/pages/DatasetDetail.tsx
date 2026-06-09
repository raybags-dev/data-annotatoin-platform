import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import PipelineProgress from '../components/PipelineProgress'

const STAGES = ['ingest', 'validate', 'clean', 'label']

// ─── Workflow guide ───────────────────────────────────────────────────────────

const WORKFLOW_STEPS: { key: string; label: string; desc: string; statusAfter: string }[] = [
  { key: 'ingest',    label: 'Ingest',    desc: 'Parse the file and store rows in the database.',         statusAfter: 'ingested' },
  { key: 'validate',  label: 'Validate',  desc: 'Detect missing values, duplicates, and schema issues.',  statusAfter: 'validated' },
  { key: 'clean',     label: 'Clean',     desc: 'Auto-fix missing values and normalise text columns.',    statusAfter: 'cleaned' },
  { key: 'label',     label: 'Label',     desc: 'Run the AI model to assign a category to every row.',   statusAfter: 'labeled' },
  { key: 'review',    label: 'Review',    desc: 'Inspect AI labels and correct any mistakes.',            statusAfter: 'reviewed' },
  { key: 'export',    label: 'Export',    desc: 'Download annotated data as CSV, JSON, or JSONL.',        statusAfter: 'exported' },
]

const STATUS_ORDER = ['uploaded', 'ingested', 'validated', 'cleaned', 'labeled', 'reviewed', 'exported']

function WorkflowGuide({ status }: { status: string }) {
  const currentIdx = STATUS_ORDER.indexOf(status)

  return (
    <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
      <h2 className="font-semibold mb-4 text-sm uppercase tracking-wide text-gray-400">Workflow</h2>
      <div className="flex flex-wrap gap-0">
        {WORKFLOW_STEPS.map((step, i) => {
          const afterIdx = STATUS_ORDER.indexOf(step.statusAfter)
          const isDone = currentIdx >= afterIdx
          const isActive = currentIdx === afterIdx - 1  // this step is next
          return (
            <div key={step.key} className="flex items-start gap-0 min-w-0">
              <div className="flex flex-col items-center">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  isDone
                    ? 'bg-indigo-600 text-white'
                    : isActive
                      ? 'bg-indigo-600/30 border-2 border-indigo-500 text-indigo-400'
                      : 'bg-gray-800 text-gray-600'
                }`}>
                  {isDone ? '✓' : i + 1}
                </div>
                {i < WORKFLOW_STEPS.length - 1 && (
                  <div className={`w-0.5 h-4 mt-1 ${isDone ? 'bg-indigo-600' : 'bg-gray-800'}`} />
                )}
              </div>
              <div className="ml-2 mb-4 min-w-0 max-w-[120px] mr-3">
                <p className={`text-xs font-semibold ${isDone ? 'text-indigo-400' : isActive ? 'text-white' : 'text-gray-600'}`}>
                  {step.label}
                </p>
                <p className="text-xs text-gray-600 leading-snug mt-0.5 hidden sm:block">{step.desc}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Data Preview ─────────────────────────────────────────────────────────────

function DataPreview({ datasetId, rowCount }: { datasetId: string; rowCount: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['dataset-preview', datasetId],
    queryFn: () => api.datasetPreview(datasetId),
  })

  if (isLoading) return <div className="text-xs text-gray-500 animate-pulse">Loading preview…</div>
  if (!data || data.rows.length === 0) return <div className="text-xs text-gray-500">No rows to preview yet.</div>

  return (
    <div>
      <p className="text-xs text-gray-500 mb-2">
        Showing first {data.rows.length} of {rowCount.toLocaleString()} rows.
      </p>
      <div className="overflow-x-auto rounded-lg border border-white/10">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="bg-gray-800/80">
              {data.columns.map(col => (
                <th key={col} className="px-3 py-2 text-left text-gray-400 font-medium whitespace-nowrap border-b border-white/10">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, ri) => (
              <tr key={ri} className={ri % 2 === 0 ? 'bg-gray-900' : 'bg-gray-900/60'}>
                {data.columns.map(col => (
                  <td key={col} className="px-3 py-1.5 text-gray-300 max-w-[200px] truncate border-b border-white/5">
                    {row[col] == null ? <span className="text-gray-600 italic">null</span> : String(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DatasetDetail() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [categories, setCategories] = useState('')
  const [labelColumnHint, setLabelColumnHint] = useState('')
  const [running, setRunning] = useState<string | null>(null)

  const { data: ds, isLoading } = useQuery({
    queryKey: ['dataset', id],
    queryFn: () => api.getDataset(id!),
    refetchInterval: running ? 2000 : false,
  })

  const runStage = useMutation({
    mutationFn: (stage: string) => { setRunning(stage); return api.runStage(id!, stage) },
    onSettled: () => { setRunning(null); qc.invalidateQueries({ queryKey: ['dataset', id] }) },
  })

  const runAll = useMutation({
    mutationFn: () => { setRunning('all'); return api.runPipeline(id!) },
    onSettled: () => { setRunning(null); qc.invalidateQueries({ queryKey: ['dataset', id] }) },
  })

  const saveConfig = useMutation({
    mutationFn: () =>
      api.setLabelingConfig(id!, {
        categories: categories.split(',').map(s => s.trim()).filter(Boolean),
        model: ds?.labeling_config?.model || 'llama3.2:3b',
        label_column_hint: labelColumnHint || undefined,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dataset', id] }),
  })

  if (isLoading || !ds) return <div className="p-8 text-gray-500 animate-pulse">Loading…</div>

  const hasIngested = ds.status !== 'uploaded'
  const currentCategories = categories || ds.labeling_config.categories.join(', ')
  const currentColumnHint = labelColumnHint || ds.labeling_config.label_column_hint || ''

  return (
    <div className="p-8 max-w-3xl space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{ds.name}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {ds.filename} · {ds.row_count.toLocaleString()} rows · {ds.column_count} cols ·{' '}
            <span className="text-indigo-400">{ds.status}</span>
            {ds.kaggle_handle && (
              <span className="ml-2 text-xs text-gray-600 font-mono">{ds.kaggle_handle}</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to={`/datasets/${id}/review`} className="text-sm border border-white/10 px-3 py-1.5 rounded-lg hover:border-indigo-500 transition-colors">Review</Link>
          <Link to={`/datasets/${id}/export`} className="text-sm border border-white/10 px-3 py-1.5 rounded-lg hover:border-indigo-500 transition-colors">Export</Link>
        </div>
      </div>

      {/* Workflow guide */}
      <WorkflowGuide status={ds.status} />

      {/* Pipeline controls */}
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

      {/* Data preview — shown after ingest */}
      {hasIngested && (
        <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
          <h2 className="font-semibold mb-3 text-sm uppercase tracking-wide text-gray-400">Data Preview</h2>
          <DataPreview datasetId={id!} rowCount={ds.row_count} />
        </div>
      )}

      {/* Label Config */}
      <div className="bg-gray-900 border border-white/10 rounded-xl p-5 space-y-4">
        <div>
          <h2 className="font-semibold text-sm uppercase tracking-wide text-gray-400">
            Label Config — What labels should the AI assign?
          </h2>
          <p className="text-xs text-gray-500 mt-2 leading-relaxed">
            The AI will read each row and assign one of these categories.
            {hasIngested
              ? ' Look at your data preview above to decide what makes sense.'
              : ' Run Ingest first to see your data and decide.'}
            {' '}For example, if rows are customer reviews, use{' '}
            <code className="text-indigo-400 bg-indigo-900/30 px-1 rounded">positive,negative,neutral</code>.
            If emails, use <code className="text-indigo-400 bg-indigo-900/30 px-1 rounded">spam,ham</code>.
          </p>
        </div>

        {/* Column hint selector — only shown once columns are known */}
        {ds.columns && ds.columns.length > 0 && (
          <div>
            <label className="text-xs text-gray-400 block mb-1">
              Column to annotate
              <span className="text-gray-600 ml-1">(which column contains the text to label?)</span>
            </label>
            <select
              value={currentColumnHint}
              onChange={e => setLabelColumnHint(e.target.value)}
              className="w-full bg-gray-800 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-indigo-500 text-gray-300"
            >
              <option value="">— auto-detect —</option>
              {ds.columns.map(col => (
                <option key={col} value={col}>{col}</option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label className="text-xs text-gray-400 block mb-1">Categories (comma-separated)</label>
          <div className="flex gap-2">
            <input
              value={currentCategories}
              onChange={e => setCategories(e.target.value)}
              placeholder="category1, category2, …"
              className="flex-1 bg-gray-800 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-indigo-500"
            />
            <button
              onClick={() => saveConfig.mutate()}
              className="text-sm bg-indigo-600/20 border border-indigo-500/40 text-indigo-400 px-4 py-2 rounded-lg hover:bg-indigo-600/30 transition-colors whitespace-nowrap"
            >
              {saveConfig.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      </div>

      {/* Validation report */}
      {ds.validation_report && (
        <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
          <h2 className="font-semibold mb-3 text-sm uppercase tracking-wide text-gray-400">Validation Report</h2>
          <div className="grid grid-cols-3 gap-3 mb-3">
            {[['Rows', ds.validation_report.total_rows], ['Duplicates', ds.validation_report.duplicate_rows], ['Issues', ds.validation_report.issues.length]].map(([k, v]) => (
              <div key={String(k)} className="bg-gray-800 rounded-lg p-3 text-center">
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

      {/* Cleaning report */}
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
