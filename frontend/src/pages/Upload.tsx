import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'

export default function Upload() {
  const nav = useNavigate()
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [err, setErr] = useState('')

  const upload = useMutation({
    mutationFn: () => api.uploadDataset(name, file!),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['datasets'] })
      nav(`/datasets/${d._id || (d as any).id}`)
    },
    onError: (e: any) => setErr(e?.response?.data?.detail || 'Upload failed'),
  })

  return (
    <div className="p-8 max-w-xl">
      <h1 className="text-2xl font-bold mb-6">Upload Dataset</h1>
      <div className="space-y-4">
        <div>
          <label className="text-sm text-gray-400 block mb-1">Dataset name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="My Dataset"
            className="w-full bg-gray-900 border border-white/10 rounded-lg px-4 py-2.5 outline-none focus:border-indigo-500" />
        </div>
        <div>
          <label className="text-sm text-gray-400 block mb-1">File (CSV, JSON, Excel, TXT)</label>
          <input type="file" accept=".csv,.json,.xlsx,.xls,.txt" onChange={e => setFile(e.target.files?.[0] || null)}
            className="w-full bg-gray-900 border border-white/10 rounded-lg px-4 py-2.5 file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:bg-indigo-600 file:text-white file:text-sm" />
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
    </div>
  )
}
