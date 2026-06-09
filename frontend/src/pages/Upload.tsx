import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { KaggleDataset, KaggleFile, KaggleDownloadResult } from '../lib/types'

// ─── helpers ──────────────────────────────────────────────────────────────────

function fmtSize(bytes: number | null | undefined): string {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

const MAX_BYTES = 150 * 1024 * 1024 // 150 MB

// ─── upload tab ───────────────────────────────────────────────────────────────

function UploadTab() {
  const nav = useNavigate()
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [err, setErr] = useState('')

  const upload = useMutation({
    mutationFn: () => api.uploadDataset(name, file!),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['datasets'] })
      nav(`/datasets/${(d as any).id}`)
    },
    onError: (e: any) => setErr(e?.response?.data?.detail || 'Upload failed'),
  })

  return (
    <div className="space-y-4 max-w-lg">
      <div>
        <label className="text-sm text-gray-400 block mb-1">Dataset name</label>
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="My Dataset"
          className="w-full bg-gray-900 border border-white/10 rounded-lg px-4 py-2.5 outline-none focus:border-indigo-500"
        />
      </div>
      <div>
        <label className="text-sm text-gray-400 block mb-1">File (CSV, JSON, Excel, TXT)</label>
        <input
          type="file"
          accept=".csv,.json,.xlsx,.xls,.txt"
          onChange={e => setFile(e.target.files?.[0] || null)}
          className="w-full bg-gray-900 border border-white/10 rounded-lg px-4 py-2.5 file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:bg-indigo-600 file:text-white file:text-sm"
        />
      </div>
      {err && <p className="text-sm text-red-400 bg-red-500/10 px-3 py-2 rounded-lg">{err}</p>}
      <button
        onClick={() => { setErr(''); upload.mutate() }}
        disabled={!name || !file || upload.isPending}
        className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors"
      >
        {upload.isPending ? 'Uploading…' : 'Upload & Register'}
      </button>
    </div>
  )
}

// ─── kaggle tab ───────────────────────────────────────────────────────────────

type KagglePhase =
  | { phase: 'search' }
  | { phase: 'results'; datasets: KaggleDataset[] }
  | { phase: 'polling'; download_id: string; handle: string }
  | { phase: 'pick'; result: KaggleDownloadResult }
  | { phase: 'ingesting' }

function KaggleTab() {
  const nav = useNavigate()
  const qc = useQueryClient()
  const [query, setQuery] = useState('')
  const [state, setState] = useState<KagglePhase>({ phase: 'search' })
  const [selectedFile, setSelectedFile] = useState<KaggleFile | null>(null)
  const [datasetName, setDatasetName] = useState('')
  const [err, setErr] = useState('')
  const [sizeWarning, setSizeWarning] = useState('')
  const pollInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── polling effect ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (state.phase !== 'polling') {
      if (pollInterval.current) {
        clearInterval(pollInterval.current)
        pollInterval.current = null
      }
      return
    }

    const { download_id } = state

    const tick = async () => {
      try {
        const status = await api.kaggleDownloadStatus(download_id)
        if (status.status === 'ready' && status.files) {
          if (pollInterval.current) {
            clearInterval(pollInterval.current)
            pollInterval.current = null
          }
          const result: KaggleDownloadResult = {
            download_id,
            handle: status.handle,
            files: status.files,
          }
          if (result.files.length === 1) setSelectedFile(result.files[0])
          setState({ phase: 'pick', result })
        } else if (status.status === 'error') {
          if (pollInterval.current) {
            clearInterval(pollInterval.current)
            pollInterval.current = null
          }
          setErr(status.error || 'Download failed')
          setState({ phase: 'search' })
        }
        // still 'pending' — keep polling
      } catch (ex: any) {
        if (pollInterval.current) {
          clearInterval(pollInterval.current)
          pollInterval.current = null
        }
        setErr(ex?.response?.data?.detail || 'Polling failed')
        setState({ phase: 'search' })
      }
    }

    pollInterval.current = setInterval(tick, 2000)
    // Run one tick immediately so we don't wait the first 2s needlessly
    tick()

    return () => {
      if (pollInterval.current) {
        clearInterval(pollInterval.current)
        pollInterval.current = null
      }
    }
  }, [state])

  async function doSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setErr('')
    setSizeWarning('')
    setState({ phase: 'results', datasets: [] })
    try {
      const results: KaggleDataset[] = await api.kaggleSearch(query.trim())
      setState({ phase: 'results', datasets: results })
    } catch (ex: any) {
      setErr(ex?.response?.data?.detail || 'Search failed — check KAGGLE_USERNAME / KAGGLE_KEY config')
      setState({ phase: 'search' })
    }
  }

  async function doDownload(dataset: KaggleDataset) {
    setErr('')
    setSizeWarning('')

    // Size warning — show but still allow with confirmation
    if (dataset.size && dataset.size > MAX_BYTES) {
      const confirmed = confirm(
        `This dataset is ${fmtSize(dataset.size)}, which exceeds the recommended 150 MB limit. ` +
        `Download may be slow or fail. Continue anyway?`
      )
      if (!confirmed) return
    }

    try {
      const response = await api.kaggleDownload(dataset.ref, dataset.size)

      // Already imported — navigate directly
      if (response.existing) {
        qc.invalidateQueries({ queryKey: ['datasets'] })
        nav(`/datasets/${response.dataset_id}`, {
          state: { note: 'Dataset already imported — showing existing record.' },
        })
        return
      }

      // Background download started — begin polling
      const { download_id, handle } = response as { download_id: string; handle: string }
      setDatasetName(dataset.title)
      setState({ phase: 'polling', download_id, handle })
    } catch (ex: any) {
      setErr(ex?.response?.data?.detail || 'Download failed')
      setState({ phase: 'search' })
    }
  }

  async function doIngest() {
    if (!selectedFile || state.phase !== 'pick') return
    setErr('')
    const result = state.result
    setState({ phase: 'ingesting' })
    try {
      const d = await api.kaggleIngest(result.download_id, selectedFile.filename, datasetName)
      qc.invalidateQueries({ queryKey: ['datasets'] })
      nav(`/datasets/${(d as any).id}`)
    } catch (ex: any) {
      setErr(ex?.response?.data?.detail || 'Ingest failed')
      setState({ phase: 'pick', result })
    }
  }

  const isBusy = state.phase === 'polling' || state.phase === 'ingesting'

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Search bar */}
      <form onSubmit={doSearch} className="flex gap-2">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search Kaggle datasets… e.g. college salaries, titanic, iris"
          className="flex-1 bg-gray-900 border border-white/10 rounded-lg px-4 py-2.5 outline-none focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={!query.trim() || isBusy}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium px-5 py-2.5 rounded-lg transition-colors whitespace-nowrap"
        >
          Search
        </button>
      </form>

      {err && (
        <p className="text-sm text-red-400 bg-red-500/10 px-3 py-2 rounded-lg">{err}</p>
      )}
      {sizeWarning && (
        <p className="text-sm text-yellow-400 bg-yellow-500/10 px-3 py-2 rounded-lg">{sizeWarning}</p>
      )}

      {/* Polling spinner */}
      {state.phase === 'polling' && (
        <div className="flex items-center gap-3 text-gray-400 py-8">
          <svg className="animate-spin h-5 w-5 text-indigo-400" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <span>
            Downloading <span className="text-indigo-400 font-mono">{state.handle}</span> from Kaggle…
            <span className="ml-2 text-xs text-gray-600">(checking every 2s)</span>
          </span>
        </div>
      )}

      {/* Ingesting spinner */}
      {state.phase === 'ingesting' && (
        <div className="flex items-center gap-3 text-gray-400 py-8">
          <svg className="animate-spin h-5 w-5 text-indigo-400" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <span>Uploading to Supabase and registering dataset…</span>
        </div>
      )}

      {/* File picker after download */}
      {state.phase === 'pick' && (
        <div className="bg-gray-900/60 border border-white/10 rounded-xl p-5 space-y-4">
          <div>
            <p className="text-sm text-gray-400 mb-1">
              {state.result.files.length === 1
                ? '1 file found in dataset'
                : `${state.result.files.length} files found — select one to annotate`}
            </p>
            <div className="space-y-2">
              {state.result.files.map(f => (
                <label
                  key={f.filename}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedFile?.filename === f.filename
                      ? 'border-indigo-500 bg-indigo-500/10'
                      : 'border-white/10 hover:border-white/25'
                  }`}
                >
                  <input
                    type="radio"
                    name="kaggle-file"
                    value={f.filename}
                    checked={selectedFile?.filename === f.filename}
                    onChange={() => setSelectedFile(f)}
                    className="accent-indigo-500"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-mono truncate">{f.filename}</p>
                  </div>
                  <span className="text-xs text-gray-500 shrink-0 uppercase">{f.type} · {fmtSize(f.size)}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm text-gray-400 block mb-1">Dataset name</label>
            <input
              value={datasetName}
              onChange={e => setDatasetName(e.target.value)}
              placeholder="Name for this dataset"
              className="w-full bg-gray-800 border border-white/10 rounded-lg px-4 py-2.5 outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={doIngest}
              disabled={!selectedFile || !datasetName.trim()}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium px-6 py-2.5 rounded-lg transition-colors"
            >
              Ingest &amp; Annotate →
            </button>
            <button
              onClick={() => setState({ phase: 'search' })}
              className="border border-white/15 hover:border-white/30 text-gray-300 font-medium px-4 py-2.5 rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Search results grid */}
      {state.phase === 'results' && (
        <div>
          {state.datasets.length === 0 ? (
            <p className="text-gray-500 py-6">No results for &quot;{query}&quot;</p>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {state.datasets.map(ds => (
                <div
                  key={ds.ref}
                  className="bg-gray-900/60 border border-white/10 rounded-xl p-4 flex flex-col gap-3 hover:border-white/25 transition-colors"
                >
                  <div className="flex-1">
                    <p className="text-xs text-indigo-400 font-mono mb-1">{ds.ref}</p>
                    <h3 className="font-semibold text-sm leading-snug line-clamp-2">{ds.title}</h3>
                    {ds.subtitle && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{ds.subtitle}</p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
                    <span title="Size" className={ds.size && ds.size > MAX_BYTES ? 'text-yellow-500' : ''}>
                      {ds.size && ds.size > MAX_BYTES ? '⚠ ' : ''}
                      {fmtSize(ds.size)}
                    </span>
                    <span title="Downloads">↓ {fmtNum(ds.download_count)}</span>
                    <span title="Votes">▲ {fmtNum(ds.vote_count)}</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => doDownload(ds)}
                      disabled={isBusy}
                      className="flex-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium py-2 rounded-lg transition-colors"
                    >
                      Use dataset
                    </button>
                    <a
                      href={ds.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="border border-white/15 hover:border-white/30 text-gray-400 text-sm px-3 py-2 rounded-lg transition-colors"
                      title="View on Kaggle"
                    >
                      ↗
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

type Tab = 'upload' | 'kaggle'

export default function Upload() {
  const [tab, setTab] = useState<Tab>('upload')

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="text-2xl font-bold mb-2">Add Dataset</h1>
      <p className="text-sm text-gray-500 mb-6">Upload a local file or search Kaggle to import a public dataset.</p>

      {/* Tab switcher */}
      <div className="flex gap-1 mb-8 bg-gray-900/60 border border-white/10 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab('upload')}
          className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'upload' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
          }`}
        >
          Upload file
        </button>
        <button
          onClick={() => setTab('kaggle')}
          className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'kaggle' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
          }`}
        >
          Search Kaggle
        </button>
      </div>

      {tab === 'upload' ? <UploadTab /> : <KaggleTab />}
    </div>
  )
}
